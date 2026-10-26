"""Temporary alias of ``evidence.projects.project_queries`` for callers not yet moved (A09)."""

import sys

from .projects import project_queries as _moved

sys.modules[__name__] = _moved
