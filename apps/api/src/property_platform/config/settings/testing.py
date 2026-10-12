import os

os.environ.setdefault("DJANGO_SECRET_KEY", "isolated-tests-only-key")

from .base import *  # noqa: E402,F403

ALLOWED_HOSTS = ["testserver", "localhost"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# SQLite is only for isolated HTTP/schema tests. Integration CI sets the flag below.
if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
    # GIS admin discovery imports GDAL even when the HTTP tests never touch geometry.
    INSTALLED_APPS = [
        app
        for app in INSTALLED_APPS  # noqa: F405
        if app != "django.contrib.gis" and not app.startswith("property_platform.modules.")
    ]
