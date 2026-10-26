"""Temporary alias of ``evidence.projects.project_psi`` for callers not yet moved (A09)."""

import sys

from .projects import project_psi as _moved

sys.modules[__name__] = _moved
