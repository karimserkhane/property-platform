import uuid

from django.db import models


class Source(models.Model):
    key = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "source"


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

    class Meta:
        db_table = "ingestion_run"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(status="running", finished_at__isnull=True)
                    | models.Q(
                        status__in=["succeeded", "quarantined", "failed"],
                        finished_at__isnull=False,
                        finished_at__gte=models.F("started_at"),
                    )
                ),
                name="ingestion_run_lifecycle_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(actor__regex=r"\S", connector_version__regex=r"\S"),
                name="ingestion_run_operator_version_present",
            ),
        ]


class Capture(models.Model):
    parent_capture = models.ForeignKey(
        "self", null=True, on_delete=models.PROTECT, related_name="derivatives"
    )
    run = models.ForeignKey(IngestionRun, on_delete=models.PROTECT, related_name="captures")
    url = models.URLField(max_length=4000)
    fetched_started_at = models.DateTimeField(null=True)
    fetched_at = models.DateTimeField()
    http_status = models.PositiveSmallIntegerField()
    content_sha256 = models.CharField(max_length=64)
    payload = models.BinaryField()
    byte_length = models.PositiveIntegerField()
    etag = models.CharField(max_length=500, blank=True)
    last_modified_raw = models.CharField(max_length=160, blank=True)
    source_published_at = models.DateTimeField(null=True)
    ingested_at = models.DateTimeField(auto_now_add=True)
    acquisition_method = models.CharField(max_length=40, default="live")
    timestamp_basis = models.CharField(max_length=80, default="collector_clock")

    class Meta:
        db_table = "capture"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(http_status__gte=100, http_status__lte=599),
                name="capture_http_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(fetched_at__gte=models.F("fetched_started_at")),
                name="capture_fetch_times_ordered",
            ),
            models.CheckConstraint(
                condition=models.Q(content_sha256__regex=r"^[0-9a-f]{64}$"),
                name="capture_sha256_format_valid",
            ),
        ]


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
        db_table = "parcel_observation"
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

    class Meta:
        db_table = "audit_event"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(action__in=["created", "updated"], parcel_revision__gte=1),
                name="parcel_audit_action_revision_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(actor__regex=r"\S", reason__regex=r"\S"),
                name="parcel_audit_operator_reason_present",
            ),
        ]


class QuarantinedObservation(models.Model):
    capture = models.ForeignKey(Capture, on_delete=models.PROTECT)
    source_record_id = models.CharField(max_length=80)
    field_path = models.CharField(max_length=160)
    raw_attributes = models.JSONField()
    reason = models.CharField(max_length=255)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "quarantined_observation"
        constraints = [
            models.UniqueConstraint(
                fields=["capture", "source_record_id"], name="quarantine_capture_identity"
            )
        ]


class MapObservation(models.Model):
    """Exactly one typed spatial target; immutable source snapshot and revision audit."""

    street = models.ForeignKey("catalog.Street", null=True, on_delete=models.PROTECT)
    building = models.ForeignKey("catalog.Building", null=True, on_delete=models.PROTECT)
    place = models.ForeignKey("catalog.Place", null=True, on_delete=models.PROTECT)
    administrative_area = models.ForeignKey(
        "catalog.AdministrativeArea", null=True, on_delete=models.PROTECT
    )
    capture = models.ForeignKey(Capture, on_delete=models.PROTECT)
    source_record_id = models.CharField(max_length=80)
    source_url = models.URLField(max_length=1000)
    raw_attributes = models.JSONField()
    record_sha256 = models.CharField(max_length=64)
    mapping_version = models.CharField(max_length=80)
    source_published_at = models.DateTimeField(null=True)
    ingested_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20)
    target_revision = models.PositiveIntegerField()
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)

    class Meta:
        db_table = "map_observation"
        constraints = [
            models.UniqueConstraint(
                fields=["capture", "source_record_id"], name="map_observation_capture_identity"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        street__isnull=False,
                        building__isnull=True,
                        place__isnull=True,
                        administrative_area__isnull=True,
                    )
                    | models.Q(
                        street__isnull=True,
                        building__isnull=False,
                        place__isnull=True,
                        administrative_area__isnull=True,
                    )
                    | models.Q(
                        street__isnull=True,
                        building__isnull=True,
                        place__isnull=False,
                        administrative_area__isnull=True,
                    )
                    | models.Q(
                        street__isnull=True,
                        building__isnull=True,
                        place__isnull=True,
                        administrative_area__isnull=False,
                    )
                ),
                name="map_observation_exactly_one_target",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    action__in=["created", "updated", "unchanged", "retired"],
                    target_revision__gte=1,
                ),
                name="map_observation_action_revision",
            ),
        ]


class ImageryScene(models.Model):
    """Small, auditable pilot previews. Original rasters stay with their provider."""

    scene_id = models.CharField(max_length=100, unique=True)
    capture = models.OneToOneField(Capture, on_delete=models.PROTECT)
    acquired_at = models.DateTimeField()
    cloud_cover_tile = models.FloatField()
    resolution_m = models.PositiveSmallIntegerField(default=10)
    west = models.FloatField()
    south = models.FloatField()
    east = models.FloatField()
    north = models.FloatField()
    preview_png = models.BinaryField()
    preview_sha256 = models.CharField(max_length=64)
    asset_url = models.URLField(max_length=2000)
    render_version = models.CharField(max_length=80)

    class Meta:
        db_table = "imagery_scene"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cloud_cover_tile__gte=0, cloud_cover_tile__lte=100),
                name="imagery_cloud_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(west__lt=models.F("east"), south__lt=models.F("north")),
                name="imagery_bounds_ordered",
            ),
        ]


class ResearchReference(models.Model):
    """A captured research reference, never a promoted factual assertion or parcel assignment."""

    capture = models.OneToOneField(Capture, on_delete=models.PROTECT)
    label = models.CharField(max_length=255)
    page_title = models.CharField(max_length=255, blank=True)
    source_kind = models.CharField(max_length=30)
    available = models.BooleanField(default=False)
    place = models.ForeignKey("catalog.Place", null=True, on_delete=models.PROTECT)
    mapping_version = models.CharField(max_length=80)

    class Meta:
        db_table = "research_reference"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    source_kind__in=[
                        "developer",
                        "authority",
                        "broker",
                        "forum",
                        "media",
                        "reference",
                    ]
                ),
                name="research_reference_kind_valid",
            )
        ]
