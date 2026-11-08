"""Expected freshness of each source family and the daily operations report (A32).

A family's freshness is the time of its latest successful run, read from
`evidence.ingestion_run`: a quarantined run applied its valid rows, so it counts. A failed
run changes nothing here and removes nothing anywhere, so a lost source keeps its
documented facts and simply becomes late.

`family_freshness` never reads the clock: it gives the moments a family becomes late and
to be reviewed, and the reader compares them with its own time. The preview read stays
cacheable by table family that way, since passing time alone changes no row.
"""

import hashlib
import json
from collections import defaultdict
from datetime import timedelta

from django.db.models import Max, Q
from django.utils import timezone

from ..models import Capture, IngestionRun, Source
from ..source_families import FAMILIES, family_of
from .journals import audit_context

SUCCESSFUL = ("succeeded", "quarantined")
REPORT_SOURCE = "source-freshness-report"
REPORT_URL = "https://property-platform.invalid/internal/source-freshness"
MAX_ITEMS = 25


def family_freshness():
    """One row per family, in registry order; the thresholds come from the latest success.

    `sources_behind` counts the sources of a family with no success, or with one older
    than its own threshold before the family's latest: the partial failures a family's
    latest date would otherwise hide.
    """
    successes = defaultdict(list)
    runs = (
        IngestionRun.objects.exclude(status="running")
        .values("source__key")
        .annotate(last=Max("finished_at", filter=Q(status__in=SUCCESSFUL)))
    )
    for row in runs:
        family = family_of(row["source__key"])
        if family is not None:
            successes[family.key].append(row["last"])
    rows = []
    for family in FAMILIES:
        last_runs = successes[family.key]
        latest = max((last for last in last_runs if last), default=None)
        late_after = timedelta(days=family.late_after_days)
        rows.append(
            {
                "family": family.key,
                "cadence_days": family.cadence_days,
                "last_success_at": latest,
                "late_from": latest + late_after if latest else None,
                "review_from": (
                    latest + timedelta(days=family.review_after_days) if latest else None
                ),
                "sources_total": len(last_runs),
                "sources_behind": sum(
                    1 for last in last_runs if last is None or last < latest - late_after
                ),
            }
        )
    return rows


def state_at(row, now):
    if row["last_success_at"] is None:
        return "never"
    if now >= row["review_from"]:
        return "review"
    return "late" if now >= row["late_from"] else "current"


def latest_report():
    """What the last daily report found in Prefect; None before its first run."""
    run = (
        IngestionRun.objects.filter(source__key=REPORT_SOURCE, status="succeeded")
        .order_by("-finished_at", "-pk")
        .values("finished_at", "summary")
        .first()
    )
    if run is None:
        return None
    return {
        "generated_at": run["finished_at"],
        "failing_deployments": run["summary"]["failing_deployments"],
        "late_queues": run["summary"]["late_queues"],
    }


def _checked(items, *keys):
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise ValueError("Operations report is not a bounded list")
    if any(not isinstance(item, dict) or set(item) != set(keys) for item in items):
        raise ValueError("Operations report item is malformed")
    return items


def _dated(row, now):
    fields = ("last_success_at", "late_from", "review_from")
    return row | {
        "state": state_at(row, now),
        **{field: row[field].isoformat() if row[field] else None for field in fields},
    }


def record_report(*, actor, run_key, operations):
    """Keep one daily report as a dated capture; the same Prefect run reports only once."""
    failing = _checked(
        operations["failing_deployments"], "deployment", "failures", "last_failed_at"
    )
    late = _checked(operations["late_queues"], "deployment", "runs", "oldest_expected_at")
    source, _ = Source.objects.get_or_create(
        key=REPORT_SOURCE,
        defaults={"name": "Source freshness and operations report", "url": REPORT_URL},
    )
    previous = IngestionRun.objects.filter(
        source=source, actor=actor, connector_version=run_key, status="succeeded"
    ).first()
    if previous:
        return {"status": "succeeded", "summary": previous.summary}
    with audit_context(actor=actor):
        run = IngestionRun.objects.create(source=source, actor=actor, connector_version=run_key)
        now = timezone.now()
        summary = {
            "generated_at": now.isoformat(),
            "families": [_dated(row, now) for row in family_freshness()],
            "failing_deployments": failing,
            "late_queues": late,
        }
        payload = json.dumps(summary, ensure_ascii=False, sort_keys=True).encode()
        Capture.objects.create(
            run=run,
            url=source.url,
            http_status=200,
            fetched_started_at=run.started_at,
            fetched_at=now,
            content_sha256=hashlib.sha256(payload).hexdigest(),
            byte_length=len(payload),
            payload=payload,
            acquisition_method="database_inventory",
            timestamp_basis="database_check_clock",
        )
        # Late sources are the report's finding, not a failure of the report.
        run.status = "succeeded"
        run.finished_at = timezone.now()
        run.summary = summary
        run.save(update_fields=["status", "finished_at", "summary"])
    return {"status": "succeeded", "summary": summary}
