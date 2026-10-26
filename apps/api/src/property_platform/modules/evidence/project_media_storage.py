"""Temporary alias of ``evidence.projects.project_media_storage`` (A09)."""

import sys

from .projects import project_media_storage as _moved

sys.modules[__name__] = _moved
