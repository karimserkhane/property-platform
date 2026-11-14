import os
import re

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
else:
    # A39: scripts/checks/api.sh names a test database per run on the shared server, so two
    # worktrees never create or drop each other's. Without it, Django's default name is used
    # (CI). Only a test_property_platform_* name is accepted: never the service database.
    test_name = os.environ.get("PROPERTY_PLATFORM_TEST_DB_NAME", "")
    if test_name:
        if not re.fullmatch(r"test_property_platform_[a-z0-9]{1,40}", test_name):
            raise ValueError("PROPERTY_PLATFORM_TEST_DB_NAME must be test_property_platform_<id>")
        DATABASES["default"]["TEST"] = {"NAME": test_name}  # noqa: F405
    # A45: a role without superuser rights cannot CREATE EXTENSION postgis, so its test database
    # is copied from the PostGIS image template, where the extension is already installed.
    test_template = os.environ.get("PROPERTY_PLATFORM_TEST_DB_TEMPLATE", "")
    if test_template:
        if test_template != "template_postgis":
            raise ValueError("PROPERTY_PLATFORM_TEST_DB_TEMPLATE must be template_postgis")
        DATABASES["default"].setdefault("TEST", {})["TEMPLATE"] = test_template  # noqa: F405
