"""Temporary alias of ``evidence.maps.map_sources`` for callers not yet moved (A09)."""

import sys

from .maps import map_sources as _moved

sys.modules[__name__] = _moved
