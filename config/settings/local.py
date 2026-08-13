from .base import *  # noqa: F403
from .base import env
from urllib.parse import unquote, urlparse


def mysql_database_config():
    database_url = env("DATABASE_URL")
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in {"mysql", "mysql2"}:
            raise RuntimeError("DATABASE_URL must use the mysql:// scheme.")
        return {
            "ENGINE": "django.db.backends.mysql",
            "NAME": unquote(parsed.path.lstrip("/")),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or 3306),
            "OPTIONS": {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"},
            "CONN_MAX_AGE": 60,
        }
    return {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("MYSQL_DATABASE", required=True),
        "USER": env("MYSQL_USER", required=True),
        "PASSWORD": env("MYSQL_PASSWORD", required=True),
        "HOST": env("MYSQL_HOST", "127.0.0.1"),
        "PORT": env("MYSQL_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "CONN_MAX_AGE": 60,
    }


DATABASES = {"default": mysql_database_config()}
