"""Temporary alias of ``evidence.maps.accessibility`` for callers not yet moved (A09)."""

import sys

from .maps import accessibility as _moved

sys.modules[__name__] = _moved
