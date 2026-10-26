"""Temporary alias of ``evidence.projects.queries`` for callers not yet moved (A09)."""

import sys

from .projects import queries as _moved

sys.modules[__name__] = _moved
