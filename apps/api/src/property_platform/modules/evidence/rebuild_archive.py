"""Temporary alias of ``evidence.rebuild.rebuild_archive`` for callers not yet moved (A09)."""

import sys

from .rebuild import rebuild_archive as _moved

sys.modules[__name__] = _moved
