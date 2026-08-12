import pytest
from django.conf import settings
from rest_framework.test import APIClient

from accounts.models import User
from wallets.models import Wallet


pytestmark = pytest.mark.django_db(transaction=True)


def test_customer_cannot_view_another_wallet():
    owner = User.objects.create_user(email="owner@example.com", name="Owner", password="StrongPass123!")
    stranger = User.objects.create_user(email="stranger@example.com", name="Stranger", password="StrongPass123!")
    item = Wallet.objects.create(owner=owner, currency="USD")
    client = APIClient(); client.force_authenticate(stranger)
    assert client.get(f"/api/wallets/{item.id}/").status_code == 404


def test_financial_api_requires_idempotency_key():
    user = User.objects.create_user(email="user@example.com", name="User", password="StrongPass123!")
    item = Wallet.objects.create(owner=user, currency="USD")
    client = APIClient(); client.force_authenticate(user)
    response = client.post("/api/wallet/deposit/", {"wallet_id": item.id, "amount": "5", "currency": "USD"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "idempotency_key_required"


def test_customer_is_denied_admin_api():
    user = User.objects.create_user(email="user2@example.com", name="User", password="StrongPass123!")
    client = APIClient(); client.force_authenticate(user)
    assert client.get("/api/admin/users/").status_code == 403


def test_registration_jwt_deposit_and_history_api_workflow():
    client = APIClient()
    registration = client.post("/api/auth/register/", {
        "name": "API Customer", "email": "api@example.com", "password": "StrongPass123!"
    })
    assert registration.status_code == 201
    token = client.post("/api/auth/token/", {"email": "api@example.com", "password": "StrongPass123!"})
    assert token.status_code == 200 and token.json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.json()['access']}")
    created = client.post("/api/wallets/", {"currency": "USD"})
    assert created.status_code == 201
    wallet_id = created.json()["id"]
    deposited = client.post("/api/wallet/deposit/", {
        "wallet_id": wallet_id, "amount": "20.0000", "currency": "USD"
    }, HTTP_IDEMPOTENCY_KEY="api-deposit-key")
    assert deposited.status_code == 200
    history = client.get("/api/wallet/transactions/?type=DEPOSIT&min_amount=20&reference=TXN-")
    assert history.status_code == 200 and history.json()["count"] == 1


def test_web_pages_require_session_and_render_dashboard():
    user = User.objects.create_user(email="web@example.com", name="Web", password="StrongPass123!")
    Wallet.objects.create(owner=user, currency="USD")
    client = APIClient()
    assert client.get("/").status_code == 302
    assert client.login(email="web@example.com", password="StrongPass123!")
    response = client.get("/")
    assert response.status_code == 200
    assert b"USD Wallet" in response.content
    assert b"Create Wallet" in response.content
    assert b"app-sidebar" in response.content
    assert b"desktop-topbar" in response.content


def test_login_and_registration_include_password_visibility_control():
    client = APIClient()
    for path in ("/login/", "/register/"):
        response = client.get(path)
        assert response.status_code == 200
        assert b'/static/js/theme.js' in response.content
    script = (settings.BASE_DIR / "static" / "js" / "theme.js").read_text()
    assert "Show password" in script
    assert "password-toggle" in script
