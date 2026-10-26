"""Temporary alias of ``evidence.rebuild.demo_package`` for callers not yet moved (A09)."""

import sys

from .rebuild import demo_package as _moved

sys.modules[__name__] = _moved
