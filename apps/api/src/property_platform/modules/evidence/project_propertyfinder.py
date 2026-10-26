"""Temporary alias of ``evidence.projects.project_propertyfinder`` (A09)."""

import sys

from .projects import project_propertyfinder as _moved

sys.modules[__name__] = _moved
