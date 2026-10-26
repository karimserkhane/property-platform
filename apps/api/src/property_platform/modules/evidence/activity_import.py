"""Temporary alias of ``evidence.projects.activity_import`` for callers not yet moved (A09)."""

import sys

from .projects import activity_import as _moved

sys.modules[__name__] = _moved
