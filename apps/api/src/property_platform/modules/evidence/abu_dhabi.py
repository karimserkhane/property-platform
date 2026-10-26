"""Temporary alias of ``evidence.sources.abu_dhabi`` for callers not yet moved (A09)."""

import sys

from .sources import abu_dhabi as _moved

sys.modules[__name__] = _moved
