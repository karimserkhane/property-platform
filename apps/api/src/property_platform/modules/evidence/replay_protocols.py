"""Temporary alias of ``evidence.rebuild.replay_protocols`` for callers not yet moved (A09)."""

import sys

from .rebuild import replay_protocols as _moved

sys.modules[__name__] = _moved
