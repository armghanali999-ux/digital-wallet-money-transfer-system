from django.conf import settings
from django.test import override_settings
from rest_framework.test import APIClient

from common.domain.exceptions import ConflictError, DomainError


def test_test_settings_are_safe_and_mysql_backed():
    assert settings.DEBUG is False
    assert settings.SECRET_KEY == "test-only-secret-key-not-for-deployment"
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.mysql"


def test_timezone_configuration_is_explicit():
    assert settings.TIME_ZONE == "Asia/Karachi"
    assert settings.USE_TZ is True


def test_health_endpoint_uses_consistent_success_shape():
    response = APIClient().get("/health/")
    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"status": "ok"}}


def test_domain_error_has_safe_stable_fields():
    error = ConflictError("State conflict.")
    assert isinstance(error, DomainError)
    assert error.code == "conflict"
    assert error.message == "State conflict."
    assert error.http_status == 409


@override_settings(ROOT_URLCONF="tests.unit.urls_for_exception_test")
def test_domain_exception_handler_returns_consistent_error_shape():
    response = APIClient().get("/domain-error/")
    assert response.status_code == 409
    assert response.json() == {"success": False, "error": {"code": "conflict", "message": "Safe conflict."}}
