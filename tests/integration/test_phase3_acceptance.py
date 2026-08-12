import pytest
from django.core.management import call_command
from django.test import override_settings
from rest_framework.test import APIClient

from accounts.models import User
from transactions.models import Transaction
from wallets.models import Wallet


pytestmark = pytest.mark.django_db(transaction=True)


def test_role_admin_has_full_transaction_visibility_without_is_staff():
    admin = User.objects.create_user(email="role-admin@example.com", name="Role Admin", password="StrongPass123!", role=User.Role.ADMIN)
    owner = User.objects.create_user(email="history-owner@example.com", name="Owner", password="StrongPass123!")
    wallet = Wallet.objects.create(owner=owner, currency="USD")
    txn = Transaction.objects.create(reference="TXN-ROLE-ADMIN", type=Transaction.Type.DEPOSIT,
        status=Transaction.Status.COMPLETED, amount=1, currency="USD", destination_wallet=wallet, actor=owner)
    client = APIClient(); client.force_authenticate(admin)
    assert client.get("/api/wallet/transactions/").json()["count"] == 1
    assert client.get(f"/api/wallet/transactions/{txn.reference}/").status_code == 200


@override_settings(DEBUG=True)
def test_seed_demo_is_safe_and_idempotent(capsys):
    call_command("seed_demo")
    first_output = capsys.readouterr().out
    assert "One-time local credentials" in first_output
    assert User.objects.filter(email__endswith="@example.test").count() == 2
    assert Wallet.objects.filter(owner__email="demo.customer@example.test").count() == 2
    call_command("seed_demo")
    second_output = capsys.readouterr().out
    assert "Existing passwords were preserved" in second_output
    assert User.objects.filter(email__endswith="@example.test").count() == 2
    assert Wallet.objects.filter(owner__email="demo.customer@example.test").count() == 2


def test_complete_customer_and_administrator_api_demonstration():
    alice_api = APIClient()
    bob_api = APIClient()
    for client, name, email in (
        (alice_api, "Alice", "acceptance-alice@example.com"),
        (bob_api, "Bob", "acceptance-bob@example.com"),
    ):
        assert client.post("/api/auth/register/", {
            "name": name, "email": email, "password": "StrongPass123!",
        }).status_code == 201
        token = client.post("/api/auth/token/", {"email": email, "password": "StrongPass123!"})
        assert token.status_code == 200
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.json()['access']}")

    alice_wallet = alice_api.post("/api/wallets/", {"currency": "USD"}).json()["id"]
    bob_wallet = bob_api.post("/api/wallets/", {"currency": "USD"}).json()["id"]
    assert alice_api.post("/api/wallet/deposit/", {
        "wallet_id": alice_wallet, "amount": "100.0000", "currency": "USD",
    }, HTTP_IDEMPOTENCY_KEY="acceptance-deposit").status_code == 200
    assert alice_api.post("/api/wallet/withdraw/", {
        "wallet_id": alice_wallet, "amount": "10.0000", "currency": "USD",
    }, HTTP_IDEMPOTENCY_KEY="acceptance-withdraw").status_code == 200
    transfer_response = alice_api.post("/api/wallet/transfer/", {
        "sender_wallet_id": alice_wallet, "recipient_wallet_id": bob_wallet,
        "amount": "25.0000", "description": "Acceptance transfer",
    }, HTTP_IDEMPOTENCY_KEY="acceptance-transfer")
    assert transfer_response.status_code == 200
    reference = transfer_response.json()["data"]["reference"]
    assert alice_api.get("/api/wallet/transactions/?type=TRANSFER").json()["count"] == 1
    assert bob_api.get(f"/api/wallet/transactions/{reference}/").status_code == 200

    admin = User.objects.create_superuser(email="acceptance-admin@example.com", name="Admin", password="StrongPass123!")
    admin_api = APIClient(); admin_api.force_authenticate(admin)
    assert admin_api.get("/api/admin/users/").status_code == 200
    assert admin_api.get("/api/admin/wallets/?q=acceptance-bob").status_code == 200
    assert admin_api.post(f"/api/admin/wallets/{bob_wallet}/freeze/", {"reason": "Acceptance review"}).status_code == 200
    blocked = bob_api.post("/api/wallet/deposit/", {
        "wallet_id": bob_wallet, "amount": "1.0000", "currency": "USD",
    }, HTTP_IDEMPOTENCY_KEY="acceptance-frozen")
    assert blocked.status_code == 409
    assert admin_api.post(f"/api/admin/wallets/{bob_wallet}/unfreeze/", {"reason": "Review completed"}).status_code == 200
    adjusted = admin_api.post(f"/api/admin/wallets/{bob_wallet}/adjust-balance/", {
        "amount": "5.0000", "reason": "Acceptance correction",
    }, HTTP_IDEMPOTENCY_KEY="acceptance-adjustment")
    assert adjusted.status_code == 200
