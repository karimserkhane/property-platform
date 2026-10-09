import os

os.environ.setdefault("DJANGO_SECRET_KEY", "local-development-key-never-use-in-production")

from .base import *  # noqa: E402,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "api", "testserver"]
