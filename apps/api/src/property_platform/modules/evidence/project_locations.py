"""Temporary alias of ``evidence.projects.project_locations`` for callers not yet moved (A09)."""

import sys

from .projects import project_locations as _moved

sys.modules[__name__] = _moved
