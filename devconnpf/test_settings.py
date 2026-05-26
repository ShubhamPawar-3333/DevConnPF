"""
Test settings for devconnpf project.

Uses SQLite in-memory database for fast testing without PostgreSQL.
"""

from .settings import *  # noqa: F401, F403

# Override database to use SQLite for testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable celery task execution in tests (run tasks synchronously)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use a fake Redis URL for tests
REDIS_URL = "redis://localhost:6379/15"

# Test Fernet key for token encryption
FERNET_KEY = "tPNXmv-T2HrWWRUOrfcNKHMm6dppF96iOqELbQ72-ag="
