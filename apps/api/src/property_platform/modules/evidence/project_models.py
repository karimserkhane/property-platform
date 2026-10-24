"""Typed project observations. Original bytes, times and source identity remain on Capture."""

import uuid

from django.db import models


class ProjectSourceCandidate(models.Model):
    """An observed catalogue link, never an automatically accepted map identity."""

    capture = models.ForeignKey("evidence.Capture", on_delete=models.PROTECT)
    project = models.ForeignKey("catalog.Project", null=True, on_delete=models.PROTECT)
    publisher_key = models.SlugField(max_length=80)
    territory_scope = models.SlugField(max_length=80)
    source_record_id = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(max_length=4000)
    source_url_sha256 = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    original_text = models.CharField(max_length=500)
    evidence_pointer = models.CharField(max_length=500)
    status = models.CharField(max_length=20, default="pending_review")
    actor = models.CharField(max_length=160)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project_source_candidate"
        constraints = [
            models.UniqueConstraint(
                fields=["capture", "source_url_sha256"], name="project_candidate_capture_url"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["pending_review", "registered"],
                    publisher_key__regex=r"\S",
                    actor__regex=r"\S",
                    evidence_pointer__regex=r"\S",
                ),
                name="project_candidate_audit_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(source_url_sha256__regex=r"^[a-f0-9]{64}$")
                & (
                    models.Q(status="registered", project__isnull=False)
                    | models.Q(status="pending_review", project__isnull=True)
                ),
                name="project_candidate_link_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["territory_scope", "publisher_key", "-ingested_at"],
                name="project_candidate_review_idx",
            )
        ]


class ProjectSnapshot(models.Model):
    project = models.ForeignKey("catalog.Project", on_delete=models.PROTECT)
    capture = models.ForeignKey("evidence.Capture", on_delete=models.PROTECT)
    terms_capture = models.ForeignKey(
        "evidence.Capture", null=True, on_delete=models.PROTECT, related_name="project_terms"
    )
    receipt_key = models.CharField(max_length=64, unique=True)
    extractor_version = models.CharField(max_length=80)
    # Exact interpretation identity (A12): the registry entry and the extraction code
    # that produced this reading. Readings made before it was recorded leave it blank.
    registry_sha256 = models.CharField(max_length=64, blank=True, default="")
    extractor_sha256 = models.CharField(max_length=64, blank=True, default="")
    source_role = models.CharField(max_length=20)
    source_kind = models.CharField(max_length=20, default="developer")
    source_name = models.CharField(max_length=255, blank=True)
    source_developer_name = models.CharField(max_length=255, blank=True)
    source_developer_role = models.CharField(max_length=20, blank=True)
    title = models.CharField(max_length=255)
    summary = models.CharField(max_length=1600, blank=True)
    language = models.CharField(max_length=20, default="en")
    acquisition_scope = models.CharField(max_length=40, default="local_research")
    source_rights_status = models.CharField(max_length=40, default="restricted")
    handover_precision = models.CharField(max_length=10, blank=True)
    handover_year = models.PositiveSmallIntegerField(null=True)
    handover_quarter = models.PositiveSmallIntegerField(null=True)
    handover_month = models.PositiveSmallIntegerField(null=True)
    handover_day = models.PositiveSmallIntegerField(null=True)
    handover_original = models.CharField(max_length=500, blank=True)
    handover_pointer = models.CharField(max_length=500, blank=True)
    total_units = models.PositiveIntegerField(null=True)
    total_units_basis = models.CharField(max_length=20, default="announced")
    total_units_original = models.CharField(max_length=500, blank=True)
    total_units_pointer = models.CharField(max_length=500, blank=True)
    actor = models.CharField(max_length=160)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project_snapshot"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    receipt_key__regex=r"^[a-f0-9]{64}$",
                    extractor_version__regex=r"\S",
                    actor__regex=r"\S",
                    source_role__in=["project", "offer"],
                    acquisition_scope="local_research",
                ),
                name="project_snapshot_identity_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(registry_sha256="")
                    | models.Q(registry_sha256__regex=r"^[a-f0-9]{64}$")
                )
                & (
                    models.Q(extractor_sha256="")
                    | models.Q(extractor_sha256__regex=r"^[a-f0-9]{64}$")
                ),
                name="project_snapshot_interpretation_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    source_kind__in=["developer", "publisher", "broker", "authority", "media"]
                ),
                name="project_source_kind_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(total_units_basis__in=["announced", "registered"]),
                name="project_total_basis_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(source_developer_name="", source_developer_role="")
                | models.Q(
                    source_developer_name__regex=r"\S",
                    source_developer_role__in=["declared", "registered"],
                ),
                name="project_source_party_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        handover_precision="",
                        handover_year__isnull=True,
                        handover_quarter__isnull=True,
                        handover_month__isnull=True,
                        handover_day__isnull=True,
                    )
                    | (
                        models.Q(
                            handover_year__isnull=False,
                            handover_year__gte=1900,
                            handover_year__lte=2200,
                        )
                        & (
                            models.Q(
                                handover_precision="year",
                                handover_quarter__isnull=True,
                                handover_month__isnull=True,
                                handover_day__isnull=True,
                            )
                            | models.Q(
                                handover_precision="quarter",
                                handover_quarter__isnull=False,
                                handover_quarter__gte=1,
                                handover_quarter__lte=4,
                                handover_month__isnull=True,
                                handover_day__isnull=True,
                            )
                            | models.Q(
                                handover_precision="month",
                                handover_month__isnull=False,
                                handover_quarter__isnull=True,
                                handover_month__gte=1,
                                handover_month__lte=12,
                                handover_day__isnull=True,
                            )
                            | models.Q(
                                handover_precision="day",
                                handover_month__isnull=False,
                                handover_day__isnull=False,
                                handover_quarter__isnull=True,
                                handover_month__gte=1,
                                handover_month__lte=12,
                                handover_day__gte=1,
                                handover_day__lte=31,
                            )
                        )
                        & models.Q(handover_original__regex=r"\S", handover_pointer__regex=r"\S")
                    )
                ),
                name="project_handover_precision_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(total_units__isnull=True)
                | models.Q(
                    total_units__gte=1,
                    total_units_original__regex=r"\S",
                    total_units_pointer__regex=r"\S",
                ),
                name="project_programme_total_valid",
            ),
        ]


class ProjectIdentityLink(models.Model):
    project = models.ForeignKey("catalog.Project", on_delete=models.PROTECT)
    building = models.ForeignKey("catalog.Building", null=True, on_delete=models.PROTECT)
    place = models.ForeignKey("catalog.Place", null=True, on_delete=models.PROTECT)
    parcel = models.ForeignKey("catalog.Parcel", null=True, on_delete=models.PROTECT)
    capture = models.ForeignKey("evidence.Capture", on_delete=models.PROTECT)
    actor = models.CharField(max_length=160)
    reason = models.CharField(max_length=500)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True)
    revoked_by = models.CharField(max_length=160, blank=True)
    revocation_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "project_identity_link"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(building__isnull=False, place__isnull=True, parcel__isnull=True)
                | models.Q(building__isnull=True, place__isnull=False, parcel__isnull=True)
                | models.Q(building__isnull=True, place__isnull=True, parcel__isnull=False),
                name="project_link_exactly_one_target",
            ),
            *[
                models.UniqueConstraint(
                    fields=[target],
                    condition=models.Q(active=True, **{f"{target}__isnull": False}),
                    name=f"project_link_active_{target}",
                )
                for target in ("building", "place", "parcel")
            ],
            models.CheckConstraint(
                condition=models.Q(actor__regex=r"\S", reason__regex=r"\S"),
                name="project_link_review_present",
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
                name="project_link_revocation_valid",
            ),
        ]


class ProjectRelation(models.Model):
    """Reviewed link from a component (tower, phase, residence) to its programme.

    Never a merge: both identities, their facts and their stock stay separate. Active
    rows follow `project_relations.json`; removed entries are revoked, not deleted.
    """

    child = models.ForeignKey(
        "catalog.Project", on_delete=models.PROTECT, related_name="parent_relations"
    )
    parent = models.ForeignKey(
        "catalog.Project", on_delete=models.PROTECT, related_name="component_relations"
    )
    kind = models.CharField(max_length=20)
    component = models.CharField(max_length=120)
    capture = models.ForeignKey("evidence.Capture", on_delete=models.PROTECT)
    basis = models.CharField(max_length=500)
    reviewed_on = models.DateField()
    actor = models.CharField(max_length=160)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True)
    revoked_by = models.CharField(max_length=160, blank=True)
    revocation_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "project_relation"
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(child=models.F("parent")), name="project_relation_distinct"
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=["part_of"]), name="project_relation_kind_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(component__regex=r"\S", basis__regex=r"\S", actor__regex=r"\S"),
                name="project_relation_review_present",
            ),
            # One active parent per component; a revoked link stays as history.
            models.UniqueConstraint(
                fields=["child"],
                condition=models.Q(active=True),
                name="project_relation_one_active_parent",
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
                name="project_relation_revocation_valid",
            ),
        ]


class ProjectTypology(models.Model):
    snapshot = models.ForeignKey(
        ProjectSnapshot, on_delete=models.PROTECT, related_name="typologies"
    )
    property_type = models.CharField(max_length=30)
    bedrooms = models.PositiveSmallIntegerField(null=True)
    original_text = models.CharField(max_length=500)
    evidence_pointer = models.CharField(max_length=500)

    class Meta:
        db_table = "project_typology"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    property_type__in=[
                        "apartment",
                        "duplex",
                        "penthouse",
                        "townhouse",
                        "villa",
                        "studio",
                        "hotel_apartment",
                    ]
                )
                & (models.Q(bedrooms__isnull=True) | models.Q(bedrooms__lte=20))
                & models.Q(original_text__regex=r"\S", evidence_pointer__regex=r"\S"),
                name="project_typology_value_valid",
            ),
            models.UniqueConstraint(
                fields=["snapshot", "property_type", "bedrooms"],
                nulls_distinct=False,
                name="project_typology_identity",
            ),
        ]


class ProjectAmenity(models.Model):
    snapshot = models.ForeignKey(
        ProjectSnapshot, on_delete=models.PROTECT, related_name="amenities"
    )
    code = models.SlugField(max_length=80)
    label = models.CharField(max_length=160)
    original_text = models.CharField(max_length=500)
    evidence_pointer = models.CharField(max_length=500)

    class Meta:
        db_table = "project_amenity"
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "code"], name="project_amenity_identity"),
            models.CheckConstraint(
                condition=models.Q(
                    code__regex=r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$",
                    label__regex=r"\S",
                    original_text__regex=r"\S",
                    evidence_pointer__regex=r"\S",
                ),
                name="project_amenity_value_valid",
            ),
        ]


class ProjectMedia(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    snapshot = models.ForeignKey(ProjectSnapshot, on_delete=models.PROTECT, related_name="media")
    asset_capture = models.ForeignKey(
        "evidence.Capture", null=True, on_delete=models.PROTECT, related_name="project_assets"
    )
    rights_capture = models.ForeignKey(
        "evidence.Capture", null=True, on_delete=models.PROTECT, related_name="project_media_rights"
    )
    kind = models.CharField(max_length=20)
    role = models.CharField(max_length=20)
    title = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=40)
    author = models.CharField(max_length=255, blank=True)
    licence_code = models.CharField(max_length=80, blank=True)
    licence_url = models.URLField(max_length=1000, blank=True)
    taken_on = models.DateField(null=True)
    source_url = models.URLField(max_length=4000)
    original_text = models.CharField(max_length=500)
    evidence_pointer = models.CharField(max_length=500)
    rights_status = models.CharField(max_length=20, default="reference_only")
    approved_at = models.DateTimeField(null=True)
    approved_by = models.CharField(max_length=160, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True)
    width = models.PositiveIntegerField(null=True)
    height = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = "project_media"
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "source_url"], name="project_media_source_identity"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(kind="image", mime_type__in=["image/jpeg", "image/png", "image/webp"])
                    | models.Q(kind="document", mime_type="application/pdf")
                    | models.Q(kind="video", mime_type__in=["video/mp4", "video/webm", "text/html"])
                    | models.Q(kind="model", mime_type="model/gltf-binary")
                )
                & models.Q(
                    role__in=[
                        "hero",
                        "gallery",
                        "brochure",
                        "factsheet",
                        "floor_plan",
                        "tour",
                        "model",
                    ],
                    title__regex=r"\S",
                    original_text__regex=r"\S",
                    evidence_pointer__regex=r"\S",
                ),
                name="project_media_type_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    rights_status__in=["reference_only", "blocked"],
                    approved_at__isnull=True,
                    approved_by="",
                )
                | models.Q(
                    rights_status="approved",
                    asset_capture__isnull=False,
                    rights_capture__isnull=False,
                    approved_at__isnull=False,
                    approved_by__regex=r"\S",
                ),
                name="project_media_approval_valid",
            ),
        ]


class ProjectMediaPublication(models.Model):
    media = models.OneToOneField(ProjectMedia, primary_key=True, on_delete=models.PROTECT)
    stored_object = models.ForeignKey("evidence.StoredObject", on_delete=models.PROTECT)
    actor = models.CharField(max_length=160)
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project_media_publication"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(actor__regex=r"\S"), name="project_media_publication_actor"
            )
        ]
