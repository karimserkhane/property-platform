"""Temporary alias of ``evidence.sources.imagery_import`` for callers not yet moved (A09)."""

import sys

from .sources import imagery_import as _moved

sys.modules[__name__] = _moved
