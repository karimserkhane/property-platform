"""Temporary alias of ``evidence.maps.map_import`` for callers not yet moved (A09)."""

import sys

from .maps import map_import as _moved

sys.modules[__name__] = _moved
