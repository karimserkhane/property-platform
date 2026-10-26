"""Temporary alias of ``evidence.maps.identity_repair`` for callers not yet moved (A09)."""

import sys

from .maps import identity_repair as _moved

sys.modules[__name__] = _moved
