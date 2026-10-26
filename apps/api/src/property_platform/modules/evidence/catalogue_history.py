"""Temporary alias of ``evidence.history.catalogue_history`` for callers not yet moved (A09)."""

import sys

from .history import catalogue_history as _moved

sys.modules[__name__] = _moved
