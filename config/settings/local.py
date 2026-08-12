from .base import *  # noqa: F403
from .base import env


DATABASES = {
    "default": {
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
}
