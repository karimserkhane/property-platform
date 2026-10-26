"""Temporary alias of ``evidence.projects.project_verification_links`` (A09)."""

import sys

from .projects import project_verification_links as _moved

sys.modules[__name__] = _moved
