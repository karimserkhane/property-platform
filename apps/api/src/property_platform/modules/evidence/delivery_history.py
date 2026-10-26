"""Temporary alias of ``evidence.projects.delivery_history`` for callers not yet moved (A09)."""

import sys

from .projects import delivery_history as _moved

sys.modules[__name__] = _moved
