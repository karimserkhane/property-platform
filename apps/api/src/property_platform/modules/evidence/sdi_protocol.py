"""Temporary alias of ``evidence.maps.sdi_protocol`` for callers not yet moved (A09)."""

import sys

from .maps import sdi_protocol as _moved

sys.modules[__name__] = _moved
