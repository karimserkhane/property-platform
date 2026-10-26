"""Temporary alias of ``evidence.maps.sdi_import`` for callers not yet moved (A09)."""

import sys

from .maps import sdi_import as _moved

sys.modules[__name__] = _moved
