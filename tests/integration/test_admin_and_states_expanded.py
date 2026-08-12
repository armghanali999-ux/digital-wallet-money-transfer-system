from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from administration.models import AdministrativeAudit
from common.domain.exceptions import ConflictError, DomainError
from transactions.models import Transaction, WalletTransaction
from wallets.models import Wallet
from wallets.services import adjust_balance, set_wallet_frozen, transition_transaction


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def admin_customer_wallet():
    admin = User.objects.create_superuser(email="phase2admin@example.com", name="Admin", password="StrongPass123!")
    customer = User.objects.create_user(email="phase2customer@example.com", name="Customer", password="StrongPass123!")
    wallet = Wallet.objects.create(owner=customer, currency="USD", balance=Decimal("20"))
    return admin, customer, wallet


@pytest.mark.parametrize("target", [Transaction.Status.COMPLETED, Transaction.Status.FAILED, Transaction.Status.CANCELLED])
def test_every_allowed_pending_transition(admin_customer_wallet, target):
    admin, _, wallet = admin_customer_wallet
    txn = Transaction.objects.create(reference=f"TXN-ALLOWED-{target}", type=Transaction.Type.DEPOSIT,
        status=Transaction.Status.PENDING, amount=1, currency="USD", destination_wallet=wallet, actor=admin)
    assert transition_transaction(txn, target).status == target


@pytest.mark.parametrize("start,target", [
    (Transaction.Status.COMPLETED, Transaction.Status.PENDING),
    (Transaction.Status.COMPLETED, Transaction.Status.FAILED),
    (Transaction.Status.FAILED, Transaction.Status.COMPLETED),
    (Transaction.Status.CANCELLED, Transaction.Status.PENDING),
    (Transaction.Status.PENDING, Transaction.Status.PENDING),
])
def test_forbidden_transitions(admin_customer_wallet, start, target):
    admin, _, wallet = admin_customer_wallet
    txn = Transaction.objects.create(reference=f"TXN-DENIED-{start}-{target}", type=Transaction.Type.DEPOSIT,
        status=start, amount=1, currency="USD", destination_wallet=wallet, actor=admin)
    with pytest.raises(ConflictError): transition_transaction(txn, target)


def test_freeze_unfreeze_requires_reason_and_valid_state(admin_customer_wallet):
    admin, _, wallet = admin_customer_wallet
    with pytest.raises(DomainError, match="Reason"): set_wallet_frozen(admin, wallet.id, True, "")
    set_wallet_frozen(admin, wallet.id, True, "Review")
    with pytest.raises(ConflictError): set_wallet_frozen(admin, wallet.id, True, "Again")
    set_wallet_frozen(admin, wallet.id, False, "Cleared")
    assert AdministrativeAudit.objects.count() == 2


def test_unfreeze_rejects_duplicate_active_currency(admin_customer_wallet):
    admin, customer, old_wallet = admin_customer_wallet
    set_wallet_frozen(admin, old_wallet.id, True, "Review")
    Wallet.objects.create(owner=customer, currency="USD")
    with pytest.raises(ConflictError, match="Another active wallet"):
        set_wallet_frozen(admin, old_wallet.id, False, "Restore")
    old_wallet.refresh_from_db(); assert old_wallet.status == Wallet.Status.FROZEN


def test_adjustment_validation_atomic_audit_and_idempotency(admin_customer_wallet):
    admin, _, wallet = admin_customer_wallet
    for invalid in ("0", "invalid"):
        with pytest.raises(DomainError): adjust_balance(admin, wallet.id, invalid, "Correction", f"invalid-{invalid}")
    with pytest.raises(DomainError, match="Reason"): adjust_balance(admin, wallet.id, "1", "", "no-reason")
    with pytest.raises(DomainError, match="negative"): adjust_balance(admin, wallet.id, "-21", "Correction", "negative")
    first = adjust_balance(admin, wallet.id, "5", "Correction", "same-adjust")
    repeated = adjust_balance(admin, wallet.id, "5", "Correction", "same-adjust")
    wallet.refresh_from_db()
    assert first == repeated and wallet.balance == Decimal("25.0000")
    assert Transaction.objects.filter(type=Transaction.Type.BALANCE_ADJUSTMENT).count() == 1
    assert WalletTransaction.objects.count() == 1 and AdministrativeAudit.objects.count() == 1


def test_admin_endpoints_enforce_permissions_and_create_audits(admin_customer_wallet):
    admin, customer, wallet = admin_customer_wallet
    customer_client = APIClient(); customer_client.force_authenticate(customer)
    assert customer_client.post(f"/api/admin/wallets/{wallet.id}/freeze/", {"reason": "x"}).status_code == 403
    admin_client = APIClient(); admin_client.force_authenticate(admin)
    assert admin_client.post(f"/api/admin/wallets/{wallet.id}/freeze/", {"reason": "Investigation"}).status_code == 200
    assert admin_client.post(f"/api/admin/wallets/{wallet.id}/unfreeze/", {"reason": "Cleared"}).status_code == 200
    adjustment = admin_client.post(f"/api/admin/wallets/{wallet.id}/adjust-balance/",
        {"amount": "2", "reason": "Correction"}, HTTP_IDEMPOTENCY_KEY="admin-api-adjust")
    assert adjustment.status_code == 200
    assert AdministrativeAudit.objects.count() == 3
