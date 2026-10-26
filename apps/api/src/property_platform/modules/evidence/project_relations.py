"""Temporary alias of ``evidence.projects.project_relations`` for callers not yet moved (A09)."""

import sys

from .projects import project_relations as _moved

sys.modules[__name__] = _moved
