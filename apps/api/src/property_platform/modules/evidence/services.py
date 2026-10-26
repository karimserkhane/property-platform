"""Temporary alias of ``evidence.maps.services`` for callers not yet moved (A09)."""

import sys

from .maps import services as _moved

sys.modules[__name__] = _moved
