"""Temporary alias of ``evidence.maps.basemap_archive`` for callers not yet moved (A09)."""

import sys

from .maps import basemap_archive as _moved

sys.modules[__name__] = _moved
