"""History policies. A missing source row is not a confirmed withdrawal."""

from contextlib import contextmanager

from django.db import connection
from django.db.models import CharField, OuterRef, Subquery, TextField

from .models import HistoryExclusion


@contextmanager
def audit_context(*, actor, execution_key=""):
    """Connection-scoped attribution, restored even on failure and pooled connections."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_setting('platform.actor', true), "
            "current_setting('platform.execution_key', true)"
        )
        previous = cursor.fetchone()
        cursor.execute(
            "SELECT set_config('platform.actor', %s, false), "
            "set_config('platform.execution_key', %s, false)",
            [actor, execution_key],
        )
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('platform.actor', %s, false), "
                "set_config('platform.execution_key', %s, false)",
                [previous[0] or "", previous[1] or ""],
            )


def context_rows(model, dataset):
    """One latest accepted version per provider ID across *all* successful snapshots.

    Filter/search only after version choice, so old names cannot revive replaced rows.
    Source IDs belong to one dataset/territory; this never matches records by proximity.
    """
    accepted = model.objects.filter(
        snapshot__dataset=dataset,
        snapshot__territory="abu-dhabi",
        snapshot__run__status="succeeded",
    )
    latest = accepted.filter(source_record_id=OuterRef("source_record_id")).order_by(
        "-snapshot__capture__fetched_at", "-snapshot__created_at", "-pk"
    )
    rows = (
        accepted.filter(pk=Subquery(latest.values("pk")[:1]))
        .exclude(
            source_record_id__in=HistoryExclusion.objects.filter(
                dataset=f"context:{dataset}", active=True
            ).values("record_key")
        )
        .select_related("snapshot__capture")
        .defer("snapshot__capture__payload")
    )
    annotations = {}
    for field in model._meta.fields:
        if isinstance(field, (CharField, TextField)) and field.name not in {
            "source_record_id",
            "field_path",
            "record_sha256",
        }:
            known = latest.exclude(**{field.name: ""})
            for attribute, value in (
                ("value", field.name),
                ("retrieved", "snapshot__capture__fetched_at"),
                ("ingested", "ingested_at"),
            ):
                annotations[f"history_{field.name}_{attribute}"] = Subquery(known.values(value)[:1])
    return rows.annotate(**annotations)


def observation_history(row, latest_snapshot):
    fields = {}
    for field in row._meta.fields:
        old = getattr(row, f"history_{field.name}_value", None)
        if getattr(row, field.name) == "" and old:
            setattr(row, field.name, old)
            fields[field.name] = {
                "retrieved_at": getattr(row, f"history_{field.name}_retrieved"),
                "ingested_at": getattr(row, f"history_{field.name}_ingested"),
            }
    return {
        "snapshot_id": row.snapshot_id,
        "retrieved_at": row.snapshot.capture.fetched_at,
        "ingested_at": row.ingested_at,
        "historical": row.snapshot_id != latest_snapshot.pk,
        "field_history": fields,
    }
