from decimal import Decimal
import uuid

import pytest
from django.test import Client
from rest_framework.test import APIClient

from accounts.models import User
from administration.models import AdministrativeAudit
from transactions.models import Transaction
from wallets.models import Wallet


pytestmark = pytest.mark.django_db(transaction=True)


def test_suspended_user_cannot_create_session_or_jwt():
    User.objects.create_user(
        email="suspended@example.com", name="Suspended", password="StrongPass123!",
        status=User.Status.SUSPENDED,
    )
    assert not Client().login(email="suspended@example.com", password="StrongPass123!")
    response = APIClient().post("/api/auth/token/", {
        "email": "suspended@example.com", "password": "StrongPass123!",
    })
    assert response.status_code == 401


def test_customer_cannot_open_purpose_built_administration():
    customer = User.objects.create_user(email="webcustomer@example.com", name="Customer", password="StrongPass123!")
    client = Client(); client.force_login(customer)
    assert client.get("/administration/").status_code == 403


def test_admin_web_freeze_adjustment_and_audit_workflow():
    admin = User.objects.create_superuser(email="webadmin@example.com", name="Admin", password="StrongPass123!")
    customer = User.objects.create_user(email="target@example.com", name="Target", password="StrongPass123!")
    wallet = Wallet.objects.create(owner=customer, currency="USD", balance=Decimal("20"))
    client = Client(); client.force_login(admin)
    assert client.get("/administration/").status_code == 200
    assert client.get(f"/administration/wallets/{wallet.id}/freeze/").status_code == 405
    assert client.post(f"/administration/wallets/{wallet.id}/freeze/", {"reason": "Investigation"}).status_code == 302
    wallet.refresh_from_db(); assert wallet.status == Wallet.Status.FROZEN
    response = client.post(f"/administration/wallets/{wallet.id}/adjust/", {
        "amount": "5.0000", "reason": "Audited correction", "idempotency_key": str(uuid.uuid4()),
    })
    assert response.status_code == 302
    wallet.refresh_from_db(); assert wallet.balance == Decimal("25.0000")
    assert AdministrativeAudit.objects.filter(wallet=wallet).count() == 2


def test_transfer_web_requires_confirmation_before_money_moves():
    sender = User.objects.create_user(email="senderweb@example.com", name="Sender", password="StrongPass123!")
    recipient = User.objects.create_user(email="recipientweb@example.com", name="Recipient", password="StrongPass123!")
    source = Wallet.objects.create(owner=sender, currency="USD", balance=Decimal("50"))
    destination = Wallet.objects.create(owner=recipient, currency="USD", balance=Decimal("10"))
    key = str(uuid.uuid4())
    payload = {"sender_wallet": source.id, "recipient_wallet_id": destination.id,
               "amount": "12.0000", "description": "Invoice", "idempotency_key": key}
    client = Client(); client.force_login(sender)
    confirmation = client.post("/transfer/", payload)
    assert confirmation.status_code == 200 and b"Confirm transfer" in confirmation.content, (
        confirmation.context.get("form").errors if confirmation.context and confirmation.context.get("form") else confirmation.content[:500]
    )
    source.refresh_from_db(); destination.refresh_from_db()
    assert source.balance == Decimal("50.0000") and destination.balance == Decimal("10.0000")
    payload["confirmed"] = "yes"
    receipt = client.post("/transfer/", payload)
    assert receipt.status_code == 200 and b"TXN-" in receipt.content
    source.refresh_from_db(); destination.refresh_from_db()
    assert source.balance == Decimal("38.0000") and destination.balance == Decimal("22.0000")
    assert Transaction.objects.filter(type=Transaction.Type.TRANSFER).count() == 1


def test_history_web_exposes_every_required_filter():
    user = User.objects.create_user(email="filtersweb@example.com", name="Filters", password="StrongPass123!")
    client = Client(); client.force_login(user)
    response = client.get("/transactions/")
    assert response.status_code == 200
    for field in (b'name="reference"', b'name="type"', b'name="status"', b'name="start_date"',
                  b'name="end_date"', b'name="min_amount"', b'name="max_amount"'):
        assert field in response.content


def test_admin_wallet_search_handles_text_and_numeric_queries():
    admin = User.objects.create_superuser(email="searchadmin@example.com", name="Admin", password="StrongPass123!")
    owner = User.objects.create_user(email="search-owner@example.com", name="Owner", password="StrongPass123!")
    wallet = Wallet.objects.create(owner=owner, currency="USD")
    client = Client(); client.force_login(admin)
    assert client.get("/administration/wallets/?q=search-owner").status_code == 200
    response = client.get(f"/administration/wallets/?q={wallet.id}")
    assert response.status_code == 200 and owner.email.encode() in response.content
