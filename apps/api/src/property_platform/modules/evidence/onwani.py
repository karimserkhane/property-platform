"""Temporary alias of ``evidence.maps.onwani`` for callers not yet moved (A09)."""

import sys

from .maps import onwani as _moved

sys.modules[__name__] = _moved
