import os

os.environ.setdefault("DJANGO_SECRET_KEY", "isolated-tests-only-key")

from .base import *  # noqa: E402,F403

ALLOWED_HOSTS = ["testserver", "localhost"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# SQLite is only for isolated HTTP/schema tests. Integration CI sets the flag below.
if os.environ.get("LIWA_TEST_POSTGIS") != "1":
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
