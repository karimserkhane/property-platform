"""Temporary alias of ``evidence.maps.osm_api_protocol`` for callers not yet moved (A09)."""

import sys

from .maps import osm_api_protocol as _moved

sys.modules[__name__] = _moved
