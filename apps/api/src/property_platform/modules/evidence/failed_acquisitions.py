"""Temporary alias of ``evidence.rebuild.failed_acquisitions`` for callers not yet moved (A09)."""

import sys

from .rebuild import failed_acquisitions as _moved

sys.modules[__name__] = _moved
