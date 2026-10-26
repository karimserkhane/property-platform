"""Temporary alias of ``evidence.projects.project_adrec`` for callers not yet moved (A09)."""

import sys

from .projects import project_adrec as _moved

sys.modules[__name__] = _moved
