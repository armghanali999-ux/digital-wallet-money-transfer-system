import hashlib
import json
from functools import wraps
from datetime import datetime, time
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from administration.models import AdministrativeAudit
from common.domain.exceptions import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from common.domain.money import money
from transactions.models import IdempotencyRecord, Transaction, WalletTransaction
from transactions.repositories import TransactionRepository
from wallets.models import Wallet
from wallets.repositories import ConfigurationRepository, WalletRepository


def _fingerprint(payload):
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalized.encode()).hexdigest()


def _limit(key):
    return Decimal(ConfigurationRepository.get(key))


def supported_currencies():
    return {x.strip().upper() for x in ConfigurationRepository.get("SUPPORTED_CURRENCIES").split(",")}


def _require_active(wallet):
    if wallet.status != Wallet.Status.ACTIVE:
        raise ConflictError("Wallet must be active for this operation.")


def _begin_idempotency(actor, operation, key, payload):
    if not key or len(key) > 128:
        raise DomainError("A valid Idempotency-Key is required.", "idempotency_key_required")
    record, created = TransactionRepository.idempotency(actor, operation, key, _fingerprint(payload))
    if record.request_fingerprint != _fingerprint(payload):
        raise ConflictError("Idempotency key was already used with a different request.")
    if not created and record.response_data and record.response_data.get("_error"):
        error = record.response_data["_error"]
        raise DomainError(error["message"], error["code"], error.get("http_status", 400))
    if not created and record.response_data:
        return record, record.response_data
    if not created:
        raise ConflictError("The identical request is currently processing.")
    return record, None


def _failure_context(operation, args, kwargs):
    actor = args[0]
    if operation in {"DEPOSIT", "WITHDRAWAL"}:
        wallet_id, raw_amount, currency, key = args[1], args[2], args[3], args[4]
        payload = {"wallet_id": wallet_id, "amount": str(money(raw_amount)), "currency": currency.upper(),
                   "description": (args[5] if len(args) > 5 else kwargs.get("description", "")).strip()}
        item = Wallet.objects.filter(id=wallet_id).first()
        return actor, key, payload, abs(Decimal(str(raw_amount))), currency.upper(), item if operation == "WITHDRAWAL" else None, item if operation == "DEPOSIT" else None
    sender_id, recipient_id, raw_amount, key = args[1], args[2], args[3], args[4]
    description = args[5] if len(args) > 5 else kwargs.get("description", "")
    payload = {"sender_id": sender_id, "recipient_id": recipient_id, "amount": str(money(raw_amount)), "description": description.strip()}
    sender = Wallet.objects.filter(id=sender_id).first(); recipient = Wallet.objects.filter(id=recipient_id).first()
    currency = sender.currency if sender else (recipient.currency if recipient else "USD")
    return actor, key, payload, abs(Decimal(str(raw_amount))), currency, sender, recipient


def _persist_failure(operation, args, kwargs, error):
    try:
        actor, key, payload, amount, currency, source, destination = _failure_context(operation, args, kwargs)
        if not key or amount <= 0:
            return
        with transaction.atomic():
            record, _ = TransactionRepository.idempotency(actor, operation, key, _fingerprint(payload))
            if record.request_fingerprint != _fingerprint(payload) or record.response_data:
                return
            txn = Transaction.objects.create(
                reference=TransactionRepository.next_reference(), type=operation,
                status=Transaction.Status.FAILED, amount=amount, currency=currency,
                source_wallet=source, destination_wallet=destination, actor=actor,
                description=payload.get("description", ""), failure_code=error.code,
                failure_reason=error.message,
            )
            record.transaction = txn
            record.response_data = {"reference": txn.reference, "_error": {
                "code": error.code, "message": error.message, "http_status": error.http_status,
            }}
            record.save(update_fields=["transaction", "response_data"])
    except Exception:
        # Failure auditing must never replace the safe business error returned
        # to the caller. Unexpected audit failures are handled during review.
        return


def audited_financial_failure(operation):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except DomainError as error:
                _persist_failure(operation, args, kwargs, error)
                raise
        return wrapper
    return decorator


def _result(txn, wallet=None):
    result = {"reference": txn.reference, "status": txn.status, "type": txn.type, "amount": str(txn.amount), "currency": txn.currency}
    if wallet is not None:
        result["balance"] = str(wallet.balance)
    return result


def create_wallet(user, currency):
    currency = currency.upper().strip()
    if currency not in supported_currencies():
        raise DomainError("Unsupported currency.", "unsupported_currency")
    try:
        with transaction.atomic():
            return Wallet.objects.create(owner=user, currency=currency)
    except Exception as exc:
        if Wallet.objects.filter(owner=user, active_currency=currency).exists():
            raise ConflictError("An active wallet already exists for this currency.") from exc
        raise


@audited_financial_failure(Transaction.Type.DEPOSIT)
@transaction.atomic
def deposit(actor, wallet_id, raw_amount, currency, key, description=""):
    amount = money(raw_amount)
    payload = {"wallet_id": wallet_id, "amount": str(amount), "currency": currency.upper(), "description": description.strip()}
    idem, prior = _begin_idempotency(actor, "DEPOSIT", key, payload)
    if prior:
        return prior
    wallets = WalletRepository.lock_many([wallet_id])
    wallet = wallets.get(int(wallet_id))
    if not wallet:
        raise NotFoundError("Wallet not found.")
    if wallet.owner_id != actor.id:
        raise PermissionDeniedError()
    _require_active(wallet)
    if wallet.currency != currency.upper():
        raise DomainError("Currency does not match wallet.", "currency_mismatch")
    if amount > _limit("MAX_SINGLE_DEPOSIT"):
        raise DomainError("Deposit exceeds the configured limit.", "limit_exceeded")
    before = wallet.balance
    wallet.balance += amount
    wallet.save(update_fields=["balance", "updated_at"])
    txn = Transaction.objects.create(reference=TransactionRepository.next_reference(), type=Transaction.Type.DEPOSIT, status=Transaction.Status.COMPLETED, amount=amount, currency=wallet.currency, destination_wallet=wallet, actor=actor, description=description)
    WalletTransaction.objects.create(transaction=txn, wallet=wallet, direction=WalletTransaction.Direction.CREDIT, amount=amount, balance_before=before, balance_after=wallet.balance)
    result = _result(txn, wallet)
    idem.transaction, idem.response_data = txn, result
    idem.save(update_fields=["transaction", "response_data"])
    return result


@audited_financial_failure(Transaction.Type.WITHDRAWAL)
@transaction.atomic
def withdraw(actor, wallet_id, raw_amount, currency, key, description=""):
    amount = money(raw_amount)
    payload = {"wallet_id": wallet_id, "amount": str(amount), "currency": currency.upper(), "description": description.strip()}
    idem, prior = _begin_idempotency(actor, "WITHDRAWAL", key, payload)
    if prior:
        return prior
    wallet = WalletRepository.lock_many([wallet_id]).get(int(wallet_id))
    if not wallet:
        raise NotFoundError("Wallet not found.")
    if wallet.owner_id != actor.id:
        raise PermissionDeniedError()
    _require_active(wallet)
    if wallet.currency != currency.upper():
        raise DomainError("Currency does not match wallet.", "currency_mismatch")
    if amount > _limit("MAX_SINGLE_WITHDRAWAL"):
        raise DomainError("Withdrawal exceeds the single-operation limit.", "limit_exceeded")
    since = timezone.make_aware(datetime.combine(timezone.localdate(), time.min))
    if Decimal(WalletRepository.daily_completed_total(wallet, Transaction.Type.WITHDRAWAL, since)) + amount > _limit("MAX_DAILY_WITHDRAWAL"):
        raise DomainError("Daily withdrawal limit exceeded.", "daily_limit_exceeded")
    if wallet.balance < amount:
        raise DomainError("Insufficient funds.", "insufficient_funds")
    before = wallet.balance
    wallet.balance -= amount
    wallet.save(update_fields=["balance", "updated_at"])
    txn = Transaction.objects.create(reference=TransactionRepository.next_reference(), type=Transaction.Type.WITHDRAWAL, status=Transaction.Status.COMPLETED, amount=amount, currency=wallet.currency, source_wallet=wallet, actor=actor, description=description)
    WalletTransaction.objects.create(transaction=txn, wallet=wallet, direction=WalletTransaction.Direction.DEBIT, amount=amount, balance_before=before, balance_after=wallet.balance)
    result = _result(txn, wallet)
    idem.transaction, idem.response_data = txn, result
    idem.save(update_fields=["transaction", "response_data"])
    return result


@audited_financial_failure(Transaction.Type.TRANSFER)
@transaction.atomic
def transfer(actor, sender_id, recipient_id, raw_amount, key, description=""):
    amount = money(raw_amount)
    payload = {"sender_id": sender_id, "recipient_id": recipient_id, "amount": str(amount), "description": description.strip()}
    idem, prior = _begin_idempotency(actor, "TRANSFER", key, payload)
    if prior:
        return prior
    if int(sender_id) == int(recipient_id):
        raise DomainError("Sender and recipient must be different.", "same_wallet")
    locked = WalletRepository.lock_many([sender_id, recipient_id])
    sender, recipient = locked.get(int(sender_id)), locked.get(int(recipient_id))
    if not sender or not recipient:
        raise NotFoundError("Sender or recipient wallet not found.")
    if sender.owner_id != actor.id:
        raise PermissionDeniedError()
    if sender.owner_id == recipient.owner_id:
        raise DomainError("You cannot transfer to yourself.", "self_transfer")
    _require_active(sender); _require_active(recipient)
    if sender.currency != recipient.currency:
        raise DomainError("Wallet currencies must match.", "currency_mismatch")
    if amount > _limit("MAX_SINGLE_TRANSFER"):
        raise DomainError("Transfer exceeds the single-operation limit.", "limit_exceeded")
    since = timezone.make_aware(datetime.combine(timezone.localdate(), time.min))
    if Decimal(WalletRepository.daily_completed_total(sender, Transaction.Type.TRANSFER, since)) + amount > _limit("MAX_DAILY_TRANSFER"):
        raise DomainError("Daily transfer limit exceeded.", "daily_limit_exceeded")
    if sender.balance < amount:
        raise DomainError("Insufficient funds.", "insufficient_funds")
    sender_before, recipient_before = sender.balance, recipient.balance
    sender.balance -= amount; recipient.balance += amount
    sender.save(update_fields=["balance", "updated_at"]); recipient.save(update_fields=["balance", "updated_at"])
    txn = Transaction.objects.create(reference=TransactionRepository.next_reference(), type=Transaction.Type.TRANSFER, status=Transaction.Status.COMPLETED, amount=amount, currency=sender.currency, source_wallet=sender, destination_wallet=recipient, actor=actor, description=description)
    WalletTransaction.objects.bulk_create([
        WalletTransaction(transaction=txn, wallet=sender, direction=WalletTransaction.Direction.DEBIT, amount=amount, balance_before=sender_before, balance_after=sender.balance),
        WalletTransaction(transaction=txn, wallet=recipient, direction=WalletTransaction.Direction.CREDIT, amount=amount, balance_before=recipient_before, balance_after=recipient.balance),
    ])
    result = _result(txn, sender); result["recipient_wallet_id"] = recipient.id
    idem.transaction, idem.response_data = txn, result; idem.save(update_fields=["transaction", "response_data"])
    return result


def transition_transaction(txn, new_status):
    allowed = {Transaction.Status.PENDING: {Transaction.Status.COMPLETED, Transaction.Status.FAILED, Transaction.Status.CANCELLED}}
    if new_status not in allowed.get(txn.status, set()):
        raise ConflictError(f"Transition from {txn.status} to {new_status} is not allowed.")
    txn.status = new_status
    txn.save(update_fields=["status", "updated_at"])
    return txn


@transaction.atomic
def set_wallet_frozen(admin, wallet_id, freeze, reason):
    if not admin.is_staff and admin.role != "ADMIN": raise PermissionDeniedError()
    if not reason.strip(): raise DomainError("Reason is required.", "reason_required")
    wallet = WalletRepository.lock_many([wallet_id]).get(int(wallet_id))
    if not wallet: raise NotFoundError("Wallet not found.")
    expected, target = (Wallet.Status.ACTIVE, Wallet.Status.FROZEN) if freeze else (Wallet.Status.FROZEN, Wallet.Status.ACTIVE)
    if wallet.status != expected: raise ConflictError("Invalid wallet status transition.")
    if not freeze and Wallet.objects.filter(owner=wallet.owner, active_currency=wallet.currency).exclude(id=wallet.id).exists():
        raise ConflictError("Another active wallet already exists for this currency.")
    wallet.status = target; wallet.save(update_fields=["status", "active_currency", "updated_at"])
    AdministrativeAudit.objects.create(administrator=admin, wallet=wallet, action=AdministrativeAudit.Action.FREEZE if freeze else AdministrativeAudit.Action.UNFREEZE, reason=reason)
    return wallet


@transaction.atomic
def adjust_balance(admin, wallet_id, raw_amount, reason, key):
    if not admin.is_staff and admin.role != "ADMIN": raise PermissionDeniedError()
    if not reason.strip(): raise DomainError("Reason is required.", "reason_required")
    try:
        adjustment = Decimal(str(raw_amount)).quantize(Decimal("0.0001"))
    except (InvalidOperation, TypeError, ValueError):
        raise DomainError("Enter a valid adjustment amount.", "invalid_amount")
    if adjustment == 0: raise DomainError("Adjustment cannot be zero.", "invalid_amount")
    payload = {"wallet_id": wallet_id, "amount": str(adjustment), "reason": reason.strip()}
    idem, prior = _begin_idempotency(admin, "BALANCE_ADJUSTMENT", key, payload)
    if prior: return prior
    wallet = WalletRepository.lock_many([wallet_id]).get(int(wallet_id))
    if not wallet: raise NotFoundError("Wallet not found.")
    before, after = wallet.balance, wallet.balance + adjustment
    if after < 0: raise DomainError("Adjustment would create a negative balance.", "insufficient_funds")
    wallet.balance = after; wallet.save(update_fields=["balance", "updated_at"])
    txn = Transaction.objects.create(reference=TransactionRepository.next_reference(), type=Transaction.Type.BALANCE_ADJUSTMENT, status=Transaction.Status.COMPLETED, amount=abs(adjustment), currency=wallet.currency, source_wallet=wallet if adjustment < 0 else None, destination_wallet=wallet if adjustment > 0 else None, actor=admin, description=reason)
    direction = WalletTransaction.Direction.CREDIT if adjustment > 0 else WalletTransaction.Direction.DEBIT
    WalletTransaction.objects.create(transaction=txn, wallet=wallet, direction=direction, amount=abs(adjustment), balance_before=before, balance_after=after)
    AdministrativeAudit.objects.create(administrator=admin, wallet=wallet, action=AdministrativeAudit.Action.BALANCE_ADJUSTMENT, reason=reason, balance_before=before, balance_after=after, transaction=txn)
    result = _result(txn, wallet); idem.transaction, idem.response_data = txn, result; idem.save(update_fields=["transaction", "response_data"])
    return result
