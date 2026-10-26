"""Temporary alias of ``evidence.maps.overture_places`` for callers not yet moved (A09)."""

import sys

from .maps import overture_places as _moved

sys.modules[__name__] = _moved
