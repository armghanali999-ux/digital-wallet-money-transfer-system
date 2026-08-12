import os


os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-for-deployment")
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "testserver,localhost")

from .base import *  # noqa: E402,F403


DEBUG = False
SECRET_KEY = "test-only-secret-key-not-for-deployment"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE", "digital_wallet"),
        "USER": os.getenv("MYSQL_USER", "digital_wallet_app"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD", ""),
        "HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "PORT": os.getenv("MYSQL_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"},
        "TEST": {"NAME": os.getenv("MYSQL_TEST_DATABASE", "test_digital_wallet")},
    }
}
