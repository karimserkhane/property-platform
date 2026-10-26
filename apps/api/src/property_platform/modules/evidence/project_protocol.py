"""Temporary alias of ``evidence.projects.project_protocol`` for callers not yet moved (A09)."""

import sys

from .projects import project_protocol as _moved

sys.modules[__name__] = _moved
