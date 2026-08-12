from decimal import Decimal

import pytest

from accounts.models import User
from administration.models import AdministrativeAudit
from common.domain.exceptions import ConflictError, DomainError
from transactions.models import Transaction, WalletTransaction
from wallets.models import Wallet
from wallets.services import adjust_balance, deposit, set_wallet_frozen, transfer, transition_transaction, withdraw


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def customers():
    first = User.objects.create_user(email="first@example.com", name="First", password="StrongPass123!")
    second = User.objects.create_user(email="second@example.com", name="Second", password="StrongPass123!")
    return first, second


def wallet(user, balance="0.0000", status=Wallet.Status.ACTIVE):
    return Wallet.objects.create(owner=user, currency="USD", balance=Decimal(balance), status=status)


def test_deposit_is_auditable_and_idempotent(customers):
    user, _ = customers; item = wallet(user)
    first = deposit(user, item.id, "25", "USD", "deposit-key")
    repeated = deposit(user, item.id, "25", "USD", "deposit-key")
    item.refresh_from_db()
    assert item.balance == Decimal("25.0000")
    assert first == repeated
    assert Transaction.objects.count() == 1
    assert WalletTransaction.objects.get().balance_after == Decimal("25.0000")


def test_idempotency_key_rejects_different_payload(customers):
    user, _ = customers; item = wallet(user)
    deposit(user, item.id, "25", "USD", "same-key")
    with pytest.raises(ConflictError): deposit(user, item.id, "26", "USD", "same-key")
    item.refresh_from_db(); assert item.balance == Decimal("25.0000")


def test_withdrawal_prevents_negative_balance(customers):
    user, _ = customers; item = wallet(user, "10")
    with pytest.raises(DomainError, match="Insufficient funds"):
        withdraw(user, item.id, "11", "USD", "withdraw-key")
    item.refresh_from_db(); assert item.balance == Decimal("10.0000")
    failed = Transaction.objects.get(status=Transaction.Status.FAILED)
    assert failed.failure_code == "insufficient_funds"


def test_failed_retry_is_audited_only_once(customers):
    user, _ = customers; item = wallet(user, "5")
    for _ in range(2):
        with pytest.raises(DomainError, match="Insufficient funds"):
            withdraw(user, item.id, "6", "USD", "failed-retry-key")
    assert Transaction.objects.filter(status=Transaction.Status.FAILED).count() == 1


def test_transfer_updates_both_wallets_and_ledger(customers):
    sender_user, recipient_user = customers
    sender, recipient = wallet(sender_user, "100"), wallet(recipient_user, "5")
    result = transfer(sender_user, sender.id, recipient.id, "40", "transfer-key", "Payment")
    sender.refresh_from_db(); recipient.refresh_from_db()
    assert (sender.balance, recipient.balance) == (Decimal("60.0000"), Decimal("45.0000"))
    assert result["reference"].startswith("TXN-")
    assert WalletTransaction.objects.filter(transaction__reference=result["reference"]).count() == 2


def test_frozen_wallet_rejects_money_operations(customers):
    user, _ = customers; item = wallet(user, "10", Wallet.Status.FROZEN)
    with pytest.raises(ConflictError): deposit(user, item.id, "1", "USD", "frozen-key")


def test_transaction_state_transitions_are_enforced(customers):
    user, _ = customers; item = wallet(user)
    txn = Transaction.objects.create(reference="TXN-TEST-STATE", type=Transaction.Type.DEPOSIT,
        status=Transaction.Status.PENDING, amount=1, currency="USD", destination_wallet=item, actor=user)
    transition_transaction(txn, Transaction.Status.COMPLETED)
    with pytest.raises(ConflictError): transition_transaction(txn, Transaction.Status.FAILED)


def test_admin_adjustment_and_freeze_are_audited(customers):
    user, _ = customers; item = wallet(user, "10")
    admin = User.objects.create_superuser(email="admin@example.com", name="Admin", password="StrongPass123!")
    adjust_balance(admin, item.id, "5", "Correction", "adjust-key")
    set_wallet_frozen(admin, item.id, True, "Investigation")
    item.refresh_from_db()
    assert item.balance == Decimal("15.0000") and item.status == Wallet.Status.FROZEN
    assert AdministrativeAudit.objects.count() == 2


def test_references_are_unique_and_human_readable(customers):
    user, _ = customers; item = wallet(user)
    first = deposit(user, item.id, "1", "USD", "reference-1")
    second = deposit(user, item.id, "1", "USD", "reference-2")
    assert first["reference"] != second["reference"]
    assert first["reference"].startswith("TXN-")
