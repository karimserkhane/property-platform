"""Temporary alias of ``evidence.maps.osm_bootstrap`` for callers not yet moved (A09)."""

import sys

from .maps import osm_bootstrap as _moved

sys.modules[__name__] = _moved
