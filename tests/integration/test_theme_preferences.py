import json

import pytest
from django.test import Client

from accounts.models import User
from accounts.themes import DEFAULT_THEME, THEMES


pytestmark = pytest.mark.django_db(transaction=True)


def test_theme_registry_contains_exact_requested_palettes():
    assert DEFAULT_THEME == "emerald_finance"
    assert THEMES["emerald_finance"]["primary"] == "#14532D"
    assert THEMES["navy_teal_fintech"]["secondary"] == "#14B8A6"
    assert THEMES["indigo_professional"]["accent"] == "#818CF8"
    assert THEMES["premium_black_gold"]["background"] == "#FAF7F0"
    assert THEMES["classic_blue"]["primary"] == "#1D4ED8"
    assert THEMES["dark_mode"]["text"] == "#F8FAFC"


def test_default_theme_and_settings_preview_cards():
    user = User.objects.create_user(email="theme@example.com", name="Theme", password="StrongPass123!")
    assert user.theme == DEFAULT_THEME
    client = Client(); client.force_login(user)
    response = client.get("/settings/")
    assert response.status_code == 200
    assert b'data-theme="emerald_finance"' in response.content
    assert response.content.count(b"data-theme-choice=") == 6
    assert b"Emerald Finance" in response.content and b"Premium Black Gold" in response.content


def test_theme_save_updates_database_and_session():
    user = User.objects.create_user(email="save@example.com", name="Save", password="StrongPass123!")
    client = Client(); client.force_login(user)
    response = client.post("/settings/theme/", data=json.dumps({"theme": "dark_mode"}), content_type="application/json")
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.theme == "dark_mode"
    assert client.session["selected_theme"] == "dark_mode"
    assert b'data-theme="dark_mode"' in client.get("/").content


def test_theme_save_works_with_csrf_enforcement_and_httponly_cookie():
    user = User.objects.create_user(email="csrf@example.com", name="CSRF", password="StrongPass123!")
    client = Client(enforce_csrf_checks=True); client.force_login(user)
    settings_page = client.get("/settings/")
    token = settings_page.context["csrf_token"]
    response = client.post(
        "/settings/theme/", data=json.dumps({"theme": "indigo_professional"}),
        content_type="application/json", HTTP_X_CSRFTOKEN=str(token),
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.theme == "indigo_professional"


def test_theme_persists_after_logout_and_login():
    user = User.objects.create_user(email="persist@example.com", name="Persist", password="StrongPass123!", theme="classic_blue")
    client = Client(); client.force_login(user)
    client.post("/logout/")
    assert client.login(email=user.email, password="StrongPass123!")
    assert b'data-theme="classic_blue"' in client.get("/").content
    assert client.session["selected_theme"] == "classic_blue"


def test_invalid_theme_is_rejected_without_changing_preference():
    user = User.objects.create_user(email="invalid@example.com", name="Invalid", password="StrongPass123!")
    client = Client(); client.force_login(user)
    response = client.post("/settings/theme/", data=json.dumps({"theme": "unknown"}), content_type="application/json")
    assert response.status_code == 400
    user.refresh_from_db()
    assert user.theme == DEFAULT_THEME


def test_theme_settings_require_authentication():
    client = Client()
    assert client.get("/settings/").status_code == 302
    assert client.post("/settings/theme/", data="{}", content_type="application/json").status_code == 302
