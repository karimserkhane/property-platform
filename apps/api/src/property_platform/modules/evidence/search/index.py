"""Rebuild and query the evidence search index (E01).

The index is derived from the published dossiers only: a rebuild reads `project_detail`
for every published project, inserts new statements, deletes those no longer published
and keeps the others untouched, so row journals record real changes only.
"""

import logging

from django.db import connection, transaction
from django.db.models import BooleanField, Exists, FloatField, OuterRef
from django.db.models.expressions import RawSQL
from django.utils import timezone

from property_platform.modules.catalog.models import Project

from ..history.journals import audit_context
from ..models import IngestionRun, Source
from ..projects.project_queries import _accepted_snapshots, project_detail, published_slugs
from ..search_models import EvidenceSearchEntry
from .claims import claims_from_dossier, project_terms, query_terms

logger = logging.getLogger(__name__)

SOURCE_KEY = "evidence-search-index"
SOURCE_URL = "https://property-platform.invalid/internal/evidence-search-index"
INDEX_VERSION = "evidence-search-v1"
# Serializes rebuilds; arbitrary constant private to this index.
LOCK = 4_101_001
MAX_RESULTS = 50
# Same expression as the GIN index of migration 0038, so PostgreSQL can use it.
VECTOR_SQL = (
    "(setweight(to_tsvector('simple'::regconfig, search_text), 'A') || "
    "setweight(to_tsvector('simple'::regconfig, project_terms), 'B'))"
)


def published_claims():
    """Every statement of the published dossiers, by claim key."""
    projects = dict(Project.objects.values_list("slug", "id"))
    result = {}
    for slug in published_slugs():
        dossier = project_detail(slug)
        terms = project_terms(dossier)
        for claim in claims_from_dossier(dossier):
            result[claim["claim_key"]] = {
                **claim,
                "project_id": projects[slug],
                "project_terms": terms,
            }
    return result


def rebuild_search_index(*, actor, run_key):
    """Bring the index to the published dossiers; idempotent per run key."""
    source, _ = Source.objects.get_or_create(
        key=SOURCE_KEY, defaults={"name": "Evidence search index", "url": SOURCE_URL}
    )
    previous = IngestionRun.objects.filter(
        source=source, connector_version=run_key, status="succeeded"
    ).first()
    if previous:
        return {"status": "succeeded", "summary": previous.summary}
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [LOCK])
        if not cursor.fetchone()[0]:
            return {"status": "succeeded", "summary": {"busy": True}}
    try:
        with audit_context(actor=actor):
            run = IngestionRun.objects.create(source=source, actor=actor, connector_version=run_key)
            try:
                with transaction.atomic():
                    summary = _apply(run)
                run.status = "succeeded"
            except Exception as exc:
                logger.error("Evidence search run %s failed", run.pk, exc_info=exc)
                run.status, run.error, summary = "failed", type(exc).__name__, {}
            run.summary = {"version": INDEX_VERSION, **summary}
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "error", "summary", "finished_at"])
            return {"status": run.status, "summary": run.summary, "error": run.error}
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [LOCK])


def _apply(run):
    wanted = published_claims()
    existing = set(EvidenceSearchEntry.objects.values_list("claim_key", flat=True))
    removed = existing - set(wanted)
    if removed:
        EvidenceSearchEntry.objects.filter(claim_key__in=removed).delete()
    EvidenceSearchEntry.objects.bulk_create(
        [EvidenceSearchEntry(run=run, **wanted[key]) for key in sorted(set(wanted) - existing)],
        batch_size=500,
    )
    return {
        "projects": len({row["project_id"] for row in wanted.values()}),
        "statements": len(wanted),
        "added": len(set(wanted) - existing),
        "removed": len(removed),
        "kept": len(existing & set(wanted)),
    }


def search_claims(query, *, territory=None, limit=20):
    """Published statements matching every word of the query, best first."""
    terms = query_terms(query)
    if not terms:
        return []
    rows = (
        EvidenceSearchEntry.objects.filter(
            RawSQL(
                f"{VECTOR_SQL} @@ to_tsquery('simple', %s)", [terms], output_field=BooleanField()
            )
        )
        .annotate(
            rank=RawSQL(
                f"ts_rank_cd({VECTOR_SQL}, to_tsquery('simple', %s))",
                [terms],
                output_field=FloatField(),
            )
        )
        # A project withdrawn since the last rebuild is never answered from the index.
        .filter(Exists(_accepted_snapshots().filter(project_id=OuterRef("project_id"))))
        .select_related("project")
        .order_by("-rank", "project__slug", "kind", "path", "claim_key")
    )
    if territory is not None:
        rows = rows.filter(project__territory_id=territory)
    return [
        {
            "claim_key": row.claim_key,
            "project": {"slug": row.project.slug, "name": row.project.name},
            "kind": row.kind,
            "path": row.path,
            "text": row.text,
            "language": row.language,
            "source": {
                "url": row.source_url,
                "name": row.source_name,
                "kind": row.source_kind,
                "content_sha256": row.content_sha256 or None,
                "evidence_pointer": row.evidence_pointer,
                "retrieved_at": row.retrieved_at,
            },
            "indexed_at": row.ingested_at,
        }
        for row in rows[: max(1, min(limit, MAX_RESULTS))]
    ]
