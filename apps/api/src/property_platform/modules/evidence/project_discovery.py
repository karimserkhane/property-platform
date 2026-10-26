"""Temporary alias of ``evidence.projects.project_discovery`` for callers not yet moved (A09)."""

import sys

from .projects import project_discovery as _moved

sys.modules[__name__] = _moved
