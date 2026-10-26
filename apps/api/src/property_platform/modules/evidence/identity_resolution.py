"""Temporary alias of ``evidence.maps.identity_resolution`` for callers not yet moved (A09)."""

import sys

from .maps import identity_resolution as _moved

sys.modules[__name__] = _moved
