"""Temporary alias of ``evidence.projects.verification_sheet`` for callers not yet moved (A09)."""

import sys

from .projects import verification_sheet as _moved

sys.modules[__name__] = _moved
