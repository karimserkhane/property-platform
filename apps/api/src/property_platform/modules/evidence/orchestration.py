"""Temporary alias of ``evidence.rebuild.orchestration`` for callers not yet moved (A09)."""

import sys

from .rebuild import orchestration as _moved

sys.modules[__name__] = _moved
