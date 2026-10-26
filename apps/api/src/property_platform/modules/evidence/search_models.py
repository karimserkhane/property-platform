"""Search index of the statements published project dossiers make (E01).

Derived data: every row is rebuilt from the published dossiers by the
`property-platform-evidence-search` flow, which keeps unchanged statements and removes
those no longer published. See docs/engineering/EVIDENCE_SEARCH.md.
"""

from django.db import models

KINDS = (
    "summary",
    "handover",
    "programme_total",
    "typologies",
    "amenity",
    "declared_progress",
    "registration",
    "component_of",
    "has_component",
)


class EvidenceSearchEntry(models.Model):
    # Digest of the statement, its project and its evidence: a stable citation identity.
    claim_key = models.CharField(max_length=64, unique=True)
    project = models.ForeignKey("catalog.Project", on_delete=models.PROTECT)
    kind = models.CharField(max_length=30)
    path = models.CharField(max_length=500)
    # The original text when the dossier carries it, else its published values joined.
    text = models.TextField()
    language = models.CharField(max_length=20)
    source_url = models.CharField(max_length=2000)
    source_name = models.CharField(max_length=255, blank=True)
    source_kind = models.CharField(max_length=20, blank=True)
    content_sha256 = models.CharField(max_length=64, blank=True)
    evidence_pointer = models.CharField(max_length=500, blank=True)
    retrieved_at = models.DateTimeField(null=True)
    # Normalized words, read by the full-text index of migration 0038.
    project_terms = models.TextField()
    search_text = models.TextField()
    run = models.ForeignKey("evidence.IngestionRun", on_delete=models.PROTECT)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evidence_search_entry"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    claim_key__regex=r"^[a-f0-9]{64}$",
                    kind__in=KINDS,
                    text__regex=r"\S",
                    source_url__regex=r"^https?://",
                )
                & (models.Q(content_sha256="") | models.Q(content_sha256__regex=r"^[a-f0-9]{64}$")),
                name="evidence_search_entry_valid",
            ),
        ]


class EvidenceSearchEmbedding(models.Model):
    """Vector of one indexed statement, computed by the pinned local model.

    Derived like its entry and removed with it. Stored as float32 bytes rather than a
    pgvector column: the shared PostGIS image has no pgvector, and the published index
    is small enough to rank in memory. See docs/engineering/EVIDENCE_SEARCH.md.
    """

    entry = models.OneToOneField(
        EvidenceSearchEntry, on_delete=models.CASCADE, related_name="embedding"
    )
    # `<model>@<revision>`: a vector from another model is recomputed, never compared.
    model = models.CharField(max_length=200)
    vector = models.BinaryField()
    run = models.ForeignKey("evidence.IngestionRun", on_delete=models.PROTECT)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evidence_search_embedding"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(model__regex=r"^[^@\s]+@[a-f0-9]{40}$"),
                name="evidence_search_embedding_valid",
            ),
        ]
