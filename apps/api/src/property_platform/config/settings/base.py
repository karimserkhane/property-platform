import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY is required.")

DEBUG = False
ALLOWED_HOSTS = []
ROOT_URLCONF = "property_platform.config.urls"
WSGI_APPLICATION = "property_platform.config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_TZ = True

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.contrib.gis",
    "property_platform.modules.catalog.apps.CatalogConfig",
    "property_platform.modules.evidence.apps.EvidenceConfig",
    "property_platform.modules.publication.apps.PublicationConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DATABASES = {
    "default": dj_database_url.config(
        default="postgresql://property_platform:property-platform-local-only@localhost:5432/property_platform",
        conn_max_age=0,
    )
}
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"
# Public first keeps Django's technical tables and extension objects there on fresh installs.
# Domain table names are unique across this fixed, trusted search path (no user schema).
DATABASES["default"].setdefault("OPTIONS", {})["options"] = (
    "-c search_path=public,real_estate,evidence"
)
STATIC_URL = "/static/"
STATIC_ROOT = "/app/staticfiles"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"

# Operator configuration only. Secrets never appear in OpenAPI or NEXT_PUBLIC_* variables.
MEDIA_STORAGE = {
    "backend": os.environ.get("MEDIA_STORAGE_BACKEND", "local"),
    "local_root": os.environ.get(
        "MEDIA_LOCAL_ROOT",
        str(Path.cwd() / ".cache" / "media"),
    ),
    "namespace": os.environ.get("MEDIA_S3_NAMESPACE", "r2-primary"),
    "endpoint_url": os.environ.get("MEDIA_S3_ENDPOINT_URL", ""),
    "region": os.environ.get("MEDIA_S3_REGION", "auto"),
    "bucket": os.environ.get("MEDIA_S3_BUCKET", ""),
    "access_key_id": os.environ.get("MEDIA_S3_ACCESS_KEY_ID", ""),
    "secret_access_key": os.environ.get("MEDIA_S3_SECRET_ACCESS_KEY", ""),
    "public_bucket": os.environ.get("MEDIA_S3_PUBLIC_BUCKET", ""),
    "public_base_url": os.environ.get("MEDIA_PUBLIC_BASE_URL", ""),
    "publication_enabled": os.environ.get("MEDIA_PUBLICATION_ENABLED", "0") == "1",
}
