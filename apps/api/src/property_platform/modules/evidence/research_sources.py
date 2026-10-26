"""Temporary alias of ``evidence.sources.research_sources`` for callers not yet moved (A09)."""

import sys

from .sources import research_sources as _moved

sys.modules[__name__] = _moved
