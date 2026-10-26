"""Temporary alias of ``evidence.projects.activity_sheet`` for callers not yet moved (A09)."""

import sys

from .projects import activity_sheet as _moved

sys.modules[__name__] = _moved
