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
from ..search_models import EvidenceSearchEmbedding, EvidenceSearchEntry
from . import embeddings
from .claims import claims_from_dossier, project_terms, query_terms

logger = logging.getLogger(__name__)

SOURCE_KEY = "evidence-search-index"
SOURCE_URL = "https://property-platform.invalid/internal/evidence-search-index"
INDEX_VERSION = "evidence-search-v1"
# Serializes rebuilds; arbitrary constant private to this index.
LOCK = 4_101_001
MAX_RESULTS = 50
# Reciprocal rank fusion constant: a rank in either list counts, neither list dominates.
FUSION_K = 60
# Same expression as the GIN index of migration 0040, so PostgreSQL can use it.
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
                summary["embeddings"] = _embed(run)
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


def _embed(run):
    """Vectors of the statements that have none for the pinned model, when available.

    The full-text index never waits for the optional service: without it, the run
    succeeds and reports why no vector was computed.
    """
    if not embeddings.configured():
        return {"status": "not_configured"}
    missing = list(
        EvidenceSearchEntry.objects.exclude(embedding__model=embeddings.MODEL_KEY)
        .select_related("project")
        .order_by("claim_key")
    )
    try:
        embeddings.check_model()
        vectors = embeddings.embed([_passage(entry) for entry in missing], role="passage")
    except embeddings.EmbeddingsUnavailable as exc:
        logger.warning("Evidence search vectors skipped: %s", exc)
        return {"status": str(exc)}
    with transaction.atomic():
        replaced, _ = EvidenceSearchEmbedding.objects.filter(entry__in=missing).delete()
        EvidenceSearchEmbedding.objects.bulk_create(
            [
                EvidenceSearchEmbedding(
                    entry=entry, model=embeddings.MODEL_KEY, vector=vector, run=run
                )
                for entry, vector in zip(missing, vectors, strict=True)
            ],
            batch_size=500,
        )
    return {
        "status": "succeeded",
        "model": embeddings.MODEL_KEY,
        "added": len(missing),
        "replaced": replaced,
    }


def _passage(entry):
    return passage_text(entry.project.name, entry.text)


def passage_text(project_name, text):
    # The project name places a statement such as a handover date under its project.
    return f"{project_name}: {text}"


def _published(rows, territory):
    # A project withdrawn since the last rebuild is never answered from the index.
    rows = rows.filter(Exists(_accepted_snapshots().filter(project_id=OuterRef("project_id"))))
    if territory is not None:
        rows = rows.filter(project__territory_id=territory)
    return rows.select_related("project")


def _limit(limit):
    return max(1, min(limit, MAX_RESULTS))


def search_claims(query, *, territory=None, limit=20):
    """Published statements matching every word of the query, best first."""
    terms = query_terms(query)
    if not terms:
        return []
    rows = _published(
        EvidenceSearchEntry.objects.filter(
            RawSQL(
                f"{VECTOR_SQL} @@ to_tsquery('simple', %s)", [terms], output_field=BooleanField()
            )
        ).annotate(
            rank=RawSQL(
                f"ts_rank_cd({VECTOR_SQL}, to_tsquery('simple', %s))",
                [terms],
                output_field=FloatField(),
            )
        ),
        territory,
    ).order_by("-rank", "project__slug", "kind", "path", "claim_key")
    return [_result(row) for row in rows[: _limit(limit)]]


def semantic_claims(query, *, territory=None, limit=20):
    """Published statements closest in meaning to the query, in any language, best first.

    Raises `EmbeddingsUnavailable` without the optional service. Every statement with a
    vector of the pinned model is ranked; there is no similarity threshold.
    """
    text = " ".join(query.split())
    if not text:
        return []
    [vector] = embeddings.embed([text], role="query")
    rows = _published(
        EvidenceSearchEntry.objects.filter(embedding__model=embeddings.MODEL_KEY), territory
    ).select_related("embedding")
    scored = sorted(
        ((embeddings.similarity(vector, row.embedding.vector), row) for row in rows),
        key=lambda pair: (-pair[0], *_order(pair[1])),
    )
    return [{**_result(row), "score": round(score, 4)} for score, row in scored[: _limit(limit)]]


def hybrid_claims(query, *, territory=None, limit=20):
    """Full-text and semantic answers fused by reciprocal rank.

    Returns the statements and whether the semantic side answered; without the optional
    service the answer is the full-text one, unchanged.
    """
    lexical = search_claims(query, territory=territory, limit=MAX_RESULTS)
    try:
        semantic = semantic_claims(query, territory=territory, limit=MAX_RESULTS)
    except embeddings.EmbeddingsUnavailable:
        return lexical[: _limit(limit)], False
    scores = fusion_scores(
        [item["claim_key"] for item in lexical], [item["claim_key"] for item in semantic]
    )
    items = {}
    for item in (*lexical, *semantic):
        items.setdefault(item["claim_key"], {k: v for k, v in item.items() if k != "score"})
    ordered = sorted(
        items.values(),
        key=lambda item: (
            -scores[item["claim_key"]],
            item["project"]["slug"],
            item["kind"],
            item["path"],
            item["claim_key"],
        ),
    )
    return ordered[: _limit(limit)], True


def fusion_scores(*rankings):
    """Reciprocal rank fusion of rankings of claim keys, best first in each."""
    scores = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking, start=1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (FUSION_K + rank)
    return scores


def _order(row):
    return (row.project.slug, row.kind, row.path, row.claim_key)


def _result(row):
    return {
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
