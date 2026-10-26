"""Temporary alias of ``evidence.sources.research_import`` for callers not yet moved (A09)."""

import sys

from .sources import research_import as _moved

sys.modules[__name__] = _moved
