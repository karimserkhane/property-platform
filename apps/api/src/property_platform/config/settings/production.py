import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

if not os.environ.get("DATABASE_URL"):
    raise ImproperlyConfigured("DATABASE_URL is required in production.")
if len(SECRET_KEY) < 50 or "local" in SECRET_KEY.lower():  # noqa: F405
    raise ImproperlyConfigured("Production requires a dedicated secret of at least 50 characters.")

ALLOWED_HOSTS = [
    host.strip() for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Explicit DJANGO_ALLOWED_HOSTS are required in production.")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
# Set proxy headers only after the trusted reverse proxy is configured and tested.
