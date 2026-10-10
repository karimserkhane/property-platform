import uuid

from django.db import models


class Source(models.Model):
    key = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)


class IngestionRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    connector_version = models.CharField(max_length=80)
    actor = models.CharField(max_length=160)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    status = models.CharField(max_length=20, default="running")
    error = models.CharField(max_length=500, blank=True)
    summary = models.JSONField(default=dict)


class Capture(models.Model):
    run = models.ForeignKey(IngestionRun, on_delete=models.PROTECT, related_name="captures")
    url = models.URLField(max_length=4000)
    fetched_started_at = models.DateTimeField()
    fetched_at = models.DateTimeField()
    http_status = models.PositiveSmallIntegerField()
    content_sha256 = models.CharField(max_length=64)
    payload = models.BinaryField()
    byte_length = models.PositiveIntegerField()
    etag = models.CharField(max_length=500, blank=True)
    last_modified_raw = models.CharField(max_length=160, blank=True)
    source_published_at = models.DateTimeField(null=True)
    ingested_at = models.DateTimeField(auto_now_add=True)


class ParcelObservation(models.Model):
    parcel = models.ForeignKey("catalog.Parcel", on_delete=models.PROTECT)
    capture = models.ForeignKey(Capture, on_delete=models.PROTECT)
    source_record_id = models.CharField(max_length=80)
    field_path = models.CharField(max_length=160)
    raw_attributes = models.JSONField()
    record_sha256 = models.CharField(max_length=64)
    source_published_at = models.DateTimeField(null=True)
    ingested_at = models.DateTimeField(auto_now_add=True)
    mapping_version = models.CharField(max_length=80)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["capture", "source_record_id"], name="observation_capture_identity"
            )
        ]


class AuditEvent(models.Model):
    run = models.ForeignKey(IngestionRun, on_delete=models.PROTECT)
    parcel = models.ForeignKey("catalog.Parcel", on_delete=models.PROTECT)
    observation = models.ForeignKey(ParcelObservation, on_delete=models.PROTECT)
    occurred_at = models.DateTimeField(auto_now_add=True)
    actor = models.CharField(max_length=160)
    action = models.CharField(max_length=20)
    reason = models.CharField(max_length=255)
    parcel_revision = models.PositiveIntegerField()
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)


class QuarantinedObservation(models.Model):
    capture = models.ForeignKey(Capture, on_delete=models.PROTECT)
    source_record_id = models.CharField(max_length=80)
    field_path = models.CharField(max_length=160)
    raw_attributes = models.JSONField()
    reason = models.CharField(max_length=255)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["capture", "source_record_id"], name="quarantine_capture_identity"
            )
        ]
