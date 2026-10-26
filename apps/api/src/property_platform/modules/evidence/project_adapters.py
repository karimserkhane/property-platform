"""Temporary alias of ``evidence.projects.project_adapters`` for callers not yet moved (A09)."""

import sys

from .projects import project_adapters as _moved

sys.modules[__name__] = _moved
