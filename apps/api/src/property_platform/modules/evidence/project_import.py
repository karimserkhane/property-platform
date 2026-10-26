"""Temporary alias of ``evidence.projects.project_import`` for callers not yet moved (A09)."""

import sys

from .projects import project_import as _moved

sys.modules[__name__] = _moved
