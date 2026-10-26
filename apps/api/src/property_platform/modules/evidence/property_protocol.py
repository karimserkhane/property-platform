"""Temporary alias of ``evidence.projects.property_protocol`` for callers not yet moved (A09)."""

import sys

from .projects import property_protocol as _moved

sys.modules[__name__] = _moved
