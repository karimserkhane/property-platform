"""Shared failure bookkeeping for ingestion runs."""

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def mark_failed(run, exc):
    """Persist a failed run with its error class only, after logging the full traceback.

    Stored diagnostics never include credentials, raw contents or SQL. The traceback goes to
    operator logs first, so it survives even when the database rejects the status update.
    """
    logger.error("Ingestion run %s failed (%s)", run.pk, type(exc).__name__, exc_info=exc)
    run.status, run.error, run.finished_at = "failed", type(exc).__name__, timezone.now()
    run.save(update_fields=["status", "error", "finished_at"])
