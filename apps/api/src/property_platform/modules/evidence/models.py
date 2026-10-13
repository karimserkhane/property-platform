import uuid

from django.db import models


class Source(models.Model):
    key = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "source"


class ParcelSourceAlias(models.Model):
    """Reviewed provider OBJECTID alias, with proof and reversible supersession."""

    source_namespace = models.CharField(max_length=120)
    source_record_id = models.CharField(max_length=80)
    parcel = models.ForeignKey(
        "catalog.Parcel", on_delete=models.PROTECT, related_name="source_aliases"
    )
    capture = models.ForeignKey("evidence.Capture", on_delete=models.PROTECT)
    superseded_parcel = models.ForeignKey(
        "catalog.Parcel", null=True, on_delete=models.PROTECT, related_name="supersession_decisions"
    )
    actor = models.CharField(max_length=160)
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    canonical_revision = models.PositiveIntegerField(default=1)
    superseded_revision = models.PositiveIntegerField(null=True)
    active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True)
    revoked_by = models.CharField(max_length=160, blank=True)
    revocation_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "parcel_source_alias"
        constraints = [
            models.UniqueConstraint(
                fields=["source_namespace", "source_record_id"],
                condition=models.Q(active=True),
                name="parcel_alias_provider_identity",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    source_namespace__regex=r"\S",
                    source_record_id__regex=r"\S",
                    actor__regex=r"\S",
                    reason__regex=r"\S",
                ),
                name="parcel_alias_audit_present",
            ),
            models.CheckConstraint(
                condition=models.Q(superseded_parcel__isnull=True)
                | ~models.Q(parcel=models.F("superseded_parcel")),
                name="parcel_alias_distinct_identities",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    active=True, revoked_at__isnull=True, revoked_by="", revocation_reason=""
                )
                | models.Q(
                    active=False,
                    revoked_at__isnull=False,
                    revoked_at__gte=models.F("created_at"),
                    revoked_by__regex=r"\S",
                    revocation_reason__regex=r"\S",
                ),
                name="parcel_alias_review_lifecycle",
            ),
            models.CheckConstraint(
                condition=models.Q(canonical_revision__gte=1)
                & (
                    models.Q(superseded_revision__isnull=True)
                    | models.Q(superseded_revision__gte=1)
                ),
                name="parcel_alias_revisions_valid",
            ),
        ]


class AdministrativeAreaSourceAlias(models.Model):
    """Provider area alias supported by identical non-OBJECTID attributes/geometry."""

    source_namespace = models.CharField(max_length=120)
    source_record_id = models.CharField(max_length=80)
    administrative_area = models.ForeignKey(
        "catalog.AdministrativeArea", on_delete=models.PROTECT, related_name="source_aliases"
    )
    capture = models.ForeignKey("evidence.Capture", on_delete=models.PROTECT)
    superseded_area = models.ForeignKey(
        "catalog.AdministrativeArea",
        null=True,
        on_delete=models.PROTECT,
        related_name="supersession_decisions",
    )
    actor = models.CharField(max_length=160)
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    canonical_revision = models.PositiveIntegerField(default=1)
    superseded_revision = models.PositiveIntegerField(null=True)
    active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True)
    revoked_by = models.CharField(max_length=160, blank=True)
    revocation_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "administrative_area_source_alias"
        constraints = [
            models.UniqueConstraint(
                fields=["source_namespace", "source_record_id"],
                condition=models.Q(active=True),
                name="area_alias_provider_identity",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    source_namespace__regex=r"\S",
                    source_record_id__regex=r"\S",
                    actor__regex=r"\S",
                    reason__regex=r"\S",
                ),
                name="area_alias_audit_present",
            ),
            models.CheckConstraint(
                condition=models.Q(superseded_area__isnull=True)
                | ~models.Q(administrative_area=models.F("superseded_area")),
                name="area_alias_distinct_identities",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    active=True, revoked_at__isnull=True, revoked_by="", revocation_reason=""
                )
                | models.Q(
                    active=False,
                    revoked_at__isnull=False,
                    revoked_at__gte=models.F("created_at"),
                    revoked_by__regex=r"\S",
                    revocation_reason__regex=r"\S",
                ),
                name="area_alias_review_lifecycle",
            ),
            models.CheckConstraint(
                condition=models.Q(canonical_revision__gte=1)
                & (
                    models.Q(superseded_revision__isnull=True)
                    | models.Q(superseded_revision__gte=1)
                ),
                name="area_alias_revisions_valid",
            ),
        ]


class PropertyPresentation(models.Model):
    """Immutable, manually reviewed presentation of one existing provider identity."""

    building = models.ForeignKey("catalog.Building", null=True, on_delete=models.PROTECT)
    place = models.ForeignKey("catalog.Place", null=True, on_delete=models.PROTECT)
    capture = models.ForeignKey("evidence.Capture", on_delete=models.PROTECT)
    display_name = models.CharField(max_length=255)
    publisher_name = models.CharField(max_length=255)
    developer_name = models.CharField(max_length=255, blank=True)
    website_url = models.URLField(max_length=1000)
    summary = models.CharField(max_length=800, blank=True)
    language = models.CharField(max_length=20, default="en")
    review_version = models.CharField(max_length=80)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "property_presentation"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(building__isnull=False, place__isnull=True)
                    | models.Q(building__isnull=True, place__isnull=False)
                ),
                name="property_presentation_one_identity",
            ),
            models.UniqueConstraint(
                fields=["capture", "building"], name="property_presentation_building_capture"
            ),
            models.UniqueConstraint(
                fields=["capture", "place"], name="property_presentation_place_capture"
            ),
        ]


class PropertyMedia(models.Model):
    """Reviewed image and licence receipt; deliberately separate from marketing facts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    presentation = models.ForeignKey(PropertyPresentation, on_delete=models.PROTECT)
    capture = models.ForeignKey("evidence.Capture", on_delete=models.PROTECT)
    licence_capture = models.ForeignKey(
        "evidence.Capture", on_delete=models.PROTECT, related_name="licensed_property_media"
    )
    source_url = models.URLField(max_length=4000)
    author = models.CharField(max_length=255)
    licence_code = models.CharField(max_length=40)
    licence_url = models.URLField(max_length=1000)
    caption = models.CharField(max_length=500)
    language = models.CharField(max_length=20, default="en")
    taken_on = models.DateField(null=True)
    mime_type = models.CharField(max_length=40)
    display_allowed = models.BooleanField(default=True)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "property_media"
        constraints = [
            models.UniqueConstraint(
                fields=["presentation", "capture"], name="property_media_presentation_capture"
            ),
            models.CheckConstraint(
                condition=models.Q(licence_code__in=["CC-BY-3.0", "CC-BY-4.0", "CC0-1.0"]),
                name="property_media_licence_allowed",
            ),
            models.CheckConstraint(
                condition=models.Q(mime_type__in=["image/jpeg", "image/png", "image/webp"]),
                name="property_media_mime_allowed",
            ),
        ]


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


class IngestionExecution(models.Model):
    """Operational identity for a scheduled attempt, separate from source evidence."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    execution_key = models.CharField(max_length=64, unique=True)
    operation = models.CharField(max_length=40)
    scope = models.CharField(max_length=100)
    actor = models.CharField(max_length=160)
    input_sha256 = models.CharField(max_length=64, null=True)
    prefect_flow_run_id = models.UUIDField(null=True)
    reused_from = models.ForeignKey(
        "self", null=True, on_delete=models.PROTECT, related_name="replays"
    )
    attempts = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    status = models.CharField(max_length=20, default="running")
    error = models.CharField(max_length=160, blank=True)
    summary = models.JSONField(default=dict)
    runs = models.ManyToManyField(
        IngestionRun, db_table="ingestion_execution_run", related_name="executions"
    )

    class Meta:
        db_table = "ingestion_execution"
        constraints = [
            models.UniqueConstraint(
                fields=["operation", "scope", "input_sha256"],
                condition=models.Q(
                    input_sha256__isnull=False, status__in=["succeeded", "quarantined"]
                ),
                name="ingestion_execution_receipt_identity",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="running", finished_at__isnull=True)
                    | models.Q(
                        status__in=["succeeded", "quarantined", "failed"],
                        finished_at__isnull=False,
                        finished_at__gte=models.F("started_at"),
                    )
                ),
                name="ingestion_execution_lifecycle_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    execution_key__regex=r"^[0-9a-f]{64}$",
                    actor__regex=r"\S",
                    attempts__gte=1,
                    operation__in=[
                        "onwani",
                        "map",
                        "references",
                        "property_presentations",
                        "imagery",
                        "osm_bootstrap",
                        "adrec_sales",
                        "adrec_indices",
                    ],
                ),
                name="ingestion_execution_identity_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(input_sha256__isnull=True)
                | models.Q(input_sha256__regex=r"^[0-9a-f]{64}$"),
                name="ingestion_execution_receipt_hash_valid",
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


class AdrecMarketSnapshot(models.Model):
    """Append-only provider snapshot, not a registry of unique transactions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.OneToOneField(IngestionRun, on_delete=models.PROTECT)
    dataset = models.CharField(max_length=20)
    territory = models.CharField(max_length=80)
    period_start = models.DateField(null=True)
    period_end = models.DateField(null=True)
    source_row_count = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "adrec_market_snapshot"
        indexes = [
            models.Index(
                fields=["territory", "dataset", "-created_at"], name="adrec_snapshot_latest"
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    dataset="sales",
                    period_start__isnull=False,
                    period_end__isnull=False,
                    period_end__gte=models.F("period_start"),
                )
                | models.Q(dataset="indices", period_start__isnull=True, period_end__isnull=True),
                name="adrec_snapshot_window_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(source_row_count__lte=10000), name="adrec_snapshot_bounded"
            ),
        ]


class AdrecSaleObservation(models.Model):
    snapshot = models.ForeignKey(
        AdrecMarketSnapshot, on_delete=models.PROTECT, related_name="sales"
    )
    capture = models.ForeignKey(Capture, on_delete=models.PROTECT)
    source_position = models.PositiveIntegerField()
    field_path = models.CharField(max_length=80)
    record_sha256 = models.CharField(max_length=64)
    registration_date = models.DateField()
    project_name = models.CharField(max_length=255, blank=True)
    district = models.CharField(max_length=255)
    community = models.CharField(max_length=255, blank=True)
    asset_class = models.CharField(max_length=255, blank=True)
    property_type = models.CharField(max_length=255, blank=True)
    property_layout = models.CharField(max_length=255, blank=True)
    sale_application_type = models.CharField(max_length=255, blank=True)
    sale_sequence = models.CharField(max_length=255, blank=True)
    price_aed = models.DecimalField(max_digits=24, decimal_places=2, null=True)
    sold_area_sqm = models.DecimalField(max_digits=24, decimal_places=8, null=True)
    plot_area_sqm = models.DecimalField(max_digits=24, decimal_places=8, null=True)
    rate_aed_per_sqm = models.DecimalField(max_digits=24, decimal_places=8, null=True)
    sold_share = models.DecimalField(max_digits=9, decimal_places=8, null=True)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "adrec_sale_observation"
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "source_position"], name="adrec_sale_position_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    price_aed__gte=0,
                    sold_area_sqm__gte=0,
                    plot_area_sqm__gte=0,
                    rate_aed_per_sqm__gte=0,
                    sold_share__gte=0,
                    sold_share__lte=1,
                ),
                name="adrec_sale_numbers_valid",
            ),
        ]


class AdrecIndexObservation(models.Model):
    snapshot = models.ForeignKey(
        AdrecMarketSnapshot, on_delete=models.PROTECT, related_name="indices"
    )
    capture = models.ForeignKey(Capture, on_delete=models.PROTECT)
    source_position = models.PositiveIntegerField()
    field_path = models.CharField(max_length=80)
    record_sha256 = models.CharField(max_length=64)
    kind = models.CharField(max_length=10)
    municipality = models.CharField(max_length=255)
    zone_label = models.CharField(max_length=255)
    property_type = models.CharField(max_length=255)
    period_end = models.DateField()
    index_value = models.DecimalField(max_digits=24, decimal_places=8, null=True)
    usable = models.BooleanField()
    review_reason = models.CharField(max_length=255, blank=True)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "adrec_index_observation"
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "kind", "source_position"], name="adrec_index_position_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=["sale", "rent"], index_value__gte=0),
                name="adrec_index_kind_value_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(usable=True, review_reason="")
                | models.Q(usable=False, review_reason__regex=r"\S"),
                name="adrec_index_review_present",
            ),
        ]
