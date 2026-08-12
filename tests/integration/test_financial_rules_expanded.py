from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db import IntegrityError

from accounts.models import User
from common.domain.exceptions import ConflictError, DomainError, PermissionDeniedError
from transactions.models import Transaction, WalletTransaction
from wallets.models import FinancialConfiguration, Wallet
from wallets.services import create_wallet, deposit, transfer, withdraw


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def users():
    return (
        User.objects.create_user(email="rules1@example.com", name="Rules 1", password="StrongPass123!"),
        User.objects.create_user(email="rules2@example.com", name="Rules 2", password="StrongPass123!"),
    )


def make_wallet(user, currency="USD", balance="0", status=Wallet.Status.ACTIVE):
    return Wallet.objects.create(owner=user, currency=currency, balance=Decimal(balance), status=status)


def configure(key, value):
    FinancialConfiguration.objects.update_or_create(key=key, defaults={"value": str(value)})


def test_wallet_currency_validation_and_active_uniqueness(users):
    user, _ = users
    first = create_wallet(user, "usd")
    assert first.currency == "USD" and first.active_currency == "USD"
    with pytest.raises(ConflictError): create_wallet(user, "USD")
    with pytest.raises(DomainError, match="Unsupported currency"): create_wallet(user, "JPY")
    first.status = Wallet.Status.FROZEN; first.save()
    assert create_wallet(user, "USD").id != first.id


@pytest.mark.parametrize("operation", ["deposit", "withdraw"])
@pytest.mark.parametrize("status", [Wallet.Status.FROZEN, Wallet.Status.CLOSED])
def test_non_active_wallet_rejects_deposit_and_withdrawal(users, operation, status):
    user, _ = users; item = make_wallet(user, balance="100", status=status)
    with pytest.raises(ConflictError):
        (deposit if operation == "deposit" else withdraw)(user, item.id, "1", "USD", f"{operation}-{status}")
    item.refresh_from_db(); assert item.balance == Decimal("100.0000")


def test_deposit_ownership_currency_positive_and_limit_rules(users):
    owner, stranger = users; item = make_wallet(owner)
    with pytest.raises(PermissionDeniedError): deposit(stranger, item.id, "1", "USD", "ownership")
    with pytest.raises(DomainError, match="Currency"): deposit(owner, item.id, "1", "PKR", "currency")
    for value in ("0", "-1", "not-money"):
        with pytest.raises(DomainError): deposit(owner, item.id, value, "USD", f"amount-{value}")
    configure("MAX_SINGLE_DEPOSIT", "10")
    deposit(owner, item.id, "10", "USD", "at-limit")
    with pytest.raises(DomainError, match="limit"): deposit(owner, item.id, "10.0001", "USD", "over-limit")
    item.refresh_from_db(); assert item.balance == Decimal("10.0000")


def test_withdrawal_single_and_daily_limits(users):
    user, _ = users; item = make_wallet(user, balance="100")
    configure("MAX_SINGLE_WITHDRAWAL", "50"); configure("MAX_DAILY_WITHDRAWAL", "60")
    withdraw(user, item.id, "40", "USD", "daily-first")
    with pytest.raises(DomainError, match="single-operation"): withdraw(user, item.id, "51", "USD", "single-over")
    with pytest.raises(DomainError, match="Daily"): withdraw(user, item.id, "21", "USD", "daily-over")
    withdraw(user, item.id, "20", "USD", "daily-exact")
    item.refresh_from_db(); assert item.balance == Decimal("40.0000")


def test_transfer_validates_identity_status_currency_limits_and_funds(users):
    sender_user, recipient_user = users
    sender = make_wallet(sender_user, balance="100")
    recipient = make_wallet(recipient_user)
    same_owner = make_wallet(sender_user, currency="PKR")
    with pytest.raises(DomainError, match="different"): transfer(sender_user, sender.id, sender.id, "1", "same-wallet")
    with pytest.raises(DomainError, match="yourself"): transfer(sender_user, sender.id, same_owner.id, "1", "self-owner")
    recipient.currency = "EUR"; recipient.save()
    with pytest.raises(DomainError, match="currencies"): transfer(sender_user, sender.id, recipient.id, "1", "mismatch")
    recipient.currency = "USD"; recipient.save()
    recipient.status = Wallet.Status.FROZEN; recipient.save()
    with pytest.raises(ConflictError): transfer(sender_user, sender.id, recipient.id, "1", "frozen-recipient")
    recipient.status = Wallet.Status.ACTIVE; recipient.save()
    configure("MAX_SINGLE_TRANSFER", "50"); configure("MAX_DAILY_TRANSFER", "60")
    with pytest.raises(DomainError, match="single-operation"): transfer(sender_user, sender.id, recipient.id, "51", "single-transfer")
    transfer(sender_user, sender.id, recipient.id, "40", "transfer-first")
    with pytest.raises(DomainError, match="Daily"): transfer(sender_user, sender.id, recipient.id, "21", "transfer-daily")
    configure("MAX_SINGLE_TRANSFER", "1000"); configure("MAX_DAILY_TRANSFER", "1000")
    with pytest.raises(DomainError, match="Insufficient"): transfer(sender_user, sender.id, recipient.id, "61", "funds")


def test_transfer_rolls_back_balances_transaction_and_ledger_on_injected_failure(users):
    sender_user, recipient_user = users
    sender, recipient = make_wallet(sender_user, balance="100"), make_wallet(recipient_user, balance="10")
    with patch("wallets.services.WalletTransaction.objects.bulk_create", side_effect=RuntimeError("injected")):
        with pytest.raises(RuntimeError, match="injected"):
            transfer(sender_user, sender.id, recipient.id, "30", "rollback-key")
    sender.refresh_from_db(); recipient.refresh_from_db()
    assert sender.balance == Decimal("100.0000") and recipient.balance == Decimal("10.0000")
    assert Transaction.objects.count() == 0 and WalletTransaction.objects.count() == 0


def test_database_constraints_reject_negative_wallet_and_invalid_ledger(users):
    user, _ = users
    with pytest.raises(IntegrityError): make_wallet(user, balance="-1")
