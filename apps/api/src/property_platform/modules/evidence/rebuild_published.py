"""Temporary alias of ``evidence.rebuild.rebuild_published`` for callers not yet moved (A09)."""

import sys

from .rebuild import rebuild_published as _moved

sys.modules[__name__] = _moved
