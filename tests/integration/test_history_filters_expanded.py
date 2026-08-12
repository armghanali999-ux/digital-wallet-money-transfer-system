from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from transactions.models import Transaction
from wallets.models import Wallet


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def history_data():
    owner = User.objects.create_user(email="history@example.com", name="History", password="StrongPass123!")
    other = User.objects.create_user(email="otherhistory@example.com", name="Other", password="StrongPass123!")
    admin = User.objects.create_superuser(email="historyadmin@example.com", name="Admin", password="StrongPass123!")
    source = Wallet.objects.create(owner=owner, currency="USD", balance=100)
    destination = Wallet.objects.create(owner=other, currency="USD")
    now = timezone.now()
    records = [
        Transaction.objects.create(reference="TXN-HISTORY-DEP", type="DEPOSIT", status="COMPLETED", amount=10, currency="USD", destination_wallet=source, actor=owner),
        Transaction.objects.create(reference="TXN-HISTORY-WITH", type="WITHDRAWAL", status="FAILED", amount=20, currency="USD", source_wallet=source, actor=owner, failure_code="insufficient_funds", failure_reason="Insufficient funds."),
        Transaction.objects.create(reference="TXN-HISTORY-OUT", type="TRANSFER", status="COMPLETED", amount=30, currency="USD", source_wallet=source, destination_wallet=destination, actor=owner),
        Transaction.objects.create(reference="TXN-HISTORY-IN", type="TRANSFER", status="COMPLETED", amount=40, currency="USD", source_wallet=destination, destination_wallet=source, actor=other),
    ]
    for index, record in enumerate(records):
        Transaction.objects.filter(id=record.id).update(created_at=now - timedelta(days=index))
    return owner, other, admin, records


def authenticated(user):
    client = APIClient(); client.force_authenticate(user); return client


def test_history_type_status_amount_reference_and_date_filters(history_data):
    owner, _, _, records = history_data; client = authenticated(owner)
    assert client.get("/api/wallet/transactions/?type=TRANSFER").json()["count"] == 2
    failed = client.get("/api/wallet/transactions/?status=FAILED").json()
    assert failed["count"] == 1 and failed["results"][0]["failure_code"] == "insufficient_funds"
    assert client.get("/api/wallet/transactions/?min_amount=20&max_amount=30").json()["count"] == 2
    assert client.get("/api/wallet/transactions/?reference=history-dep").json()["count"] == 1
    date = timezone.localdate() - timedelta(days=1)
    assert client.get(f"/api/wallet/transactions/?start_date={date}&end_date={date}").json()["count"] == 1


def test_history_marks_transfer_direction_and_stable_order(history_data):
    owner, _, _, _ = history_data; results = authenticated(owner).get("/api/wallet/transactions/?type=TRANSFER").json()["results"]
    assert [item["direction"] for item in results] == ["OUTGOING", "INCOMING"]
    assert [item["reference"] for item in results] == ["TXN-HISTORY-OUT", "TXN-HISTORY-IN"]


def test_history_pagination(history_data):
    owner, _, _, records = history_data
    wallet = records[0].destination_wallet
    for index in range(18):
        Transaction.objects.create(reference=f"TXN-PAGE-{index:02d}", type="DEPOSIT", status="COMPLETED",
            amount=1, currency="USD", destination_wallet=wallet, actor=owner)
    response = authenticated(owner).get("/api/wallet/transactions/").json()
    assert response["count"] == 22 and len(response["results"]) == 20 and response["next"]
    second_page = authenticated(owner).get("/api/wallet/transactions/?page=2").json()
    assert len(second_page["results"]) == 2 and second_page["previous"]


def test_transaction_detail_enforces_ownership_and_admin_visibility(history_data):
    owner, other, admin, _ = history_data
    outsider = User.objects.create_user(email="outsider@example.com", name="Out", password="StrongPass123!")
    assert authenticated(owner).get("/api/wallet/transactions/TXN-HISTORY-DEP/").status_code == 200
    assert authenticated(outsider).get("/api/wallet/transactions/TXN-HISTORY-DEP/").status_code == 404
    assert authenticated(admin).get("/api/wallet/transactions/TXN-HISTORY-DEP/").status_code == 200
    assert authenticated(admin).get("/api/wallet/transactions/?status=FAILED").json()["count"] == 1
