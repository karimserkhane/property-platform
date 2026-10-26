"""Temporary alias of ``evidence.sources.adrec`` for callers not yet moved (A09)."""

import sys

from .sources import adrec as _moved

sys.modules[__name__] = _moved
