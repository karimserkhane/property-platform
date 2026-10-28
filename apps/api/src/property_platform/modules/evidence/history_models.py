"""Technical row journal and explicit publication exclusions, not business observations."""

from django.db import models


class RowRevision(models.Model):
    schema_name = models.CharField(max_length=63)
    table_name = models.CharField(max_length=63)
    row_key = models.CharField(max_length=200)
    operation = models.CharField(max_length=10)
    recorded_at = models.DateTimeField()
    known_ingested_at = models.DateTimeField(null=True)
    transaction_id = models.CharField(max_length=30)
    actor = models.CharField(max_length=200)
    execution_key = models.CharField(max_length=64, blank=True)
    before = models.JSONField(null=True)
    after = models.JSONField(null=True)

    class Meta:
        db_table = "row_revision"
        indexes = [
            models.Index(
                fields=["schema_name", "table_name", "row_key", "-id"],
                name="row_revision_identity_idx",
            ),
            models.Index(fields=["recorded_at"], name="row_revision_time_idx"),
            models.Index(fields=["execution_key"], name="row_revision_execution_idx"),
            # Read-cache versions: latest revision per table, writes of pending transactions.
            models.Index(fields=["schema_name", "table_name", "id"], name="row_revision_table_idx"),
            models.Index(
                fields=["transaction_id", "schema_name", "table_name"],
                name="row_revision_transaction_idx",
            ),
        ]


class HistoryExclusion(models.Model):
    """Reviewed tombstone. Absence alone never creates one; retain the evidence."""

    dataset = models.CharField(max_length=80)
    record_key = models.CharField(max_length=4000)
    capture = models.ForeignKey("evidence.Capture", on_delete=models.PROTECT)
    reason = models.CharField(max_length=1000)
    actor = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True)
    revoked_by = models.CharField(max_length=160, blank=True)
    revocation_reason = models.CharField(max_length=1000, blank=True)

    class Meta:
        db_table = "history_exclusion"
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "record_key"],
                condition=models.Q(active=True),
                name="history_exclusion_active_key",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    reason__regex=r"\S",
                    actor__regex=r"\S",
                    dataset__regex=r"\S",
                    record_key__regex=r"\S",
                ),
                name="history_exclusion_reason_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    active=True, revoked_at__isnull=True, revoked_by="", revocation_reason=""
                )
                | (
                    models.Q(
                        active=False,
                        revoked_at__isnull=False,
                        revoked_by__regex=r"\S",
                        revocation_reason__regex=r"\S",
                    )
                ),
                name="history_exclusion_revocation_valid",
            ),
        ]
