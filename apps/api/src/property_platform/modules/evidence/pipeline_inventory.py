"""Temporary alias of ``evidence.history.pipeline_inventory`` for callers not yet moved (A09)."""

import sys

from .history import pipeline_inventory as _moved

sys.modules[__name__] = _moved
