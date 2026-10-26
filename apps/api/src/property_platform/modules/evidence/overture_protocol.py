"""Temporary alias of ``evidence.maps.overture_protocol`` for callers not yet moved (A09)."""

import sys

from .maps import overture_protocol as _moved

sys.modules[__name__] = _moved
