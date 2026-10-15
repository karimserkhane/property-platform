import uuid

from django.contrib.gis.db import models
from django.contrib.gis.db.models.functions import IsEmpty, IsValid


class Developer(models.Model):
    """Reviewed commercial identity, separate from the name found on a map feature."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    website_url = models.URLField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "developer"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(key__regex=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", name__regex=r"\S"),
                name="developer_identity_present",
            ),
        ]


class Project(models.Model):
    """Stable commercial identity; its reviewed map associations belong to evidence."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    territory_id = models.SlugField(max_length=100)
    developer = models.ForeignKey(Developer, on_delete=models.PROTECT)
    website_url = models.URLField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    slug__regex=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
                    name__regex=r"\S",
                    territory_id__regex=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
                ),
                name="project_identity_present",
            ),
        ]


class Parcel(models.Model):
    """Source-reconciled catalogue identity, not an automatically published dossier."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_namespace = models.CharField(max_length=120)
    source_record_id = models.CharField(max_length=80)
    superseded_by = models.ForeignKey(
        "self", null=True, on_delete=models.PROTECT, related_name="superseded_parcels"
    )
    official_plot_id = models.CharField(max_length=80, blank=True)
    code = models.CharField(max_length=160, blank=True)
    municipality = models.CharField(max_length=80)
    district = models.CharField(max_length=160)
    community = models.CharField(max_length=160, blank=True)
    land_use = models.CharField(max_length=255, blank=True)
    construction_status = models.CharField(max_length=160, blank=True)
    geometry = models.MultiPolygonField(srid=4326)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Resolved in real_estate by the fixed PostgreSQL search_path.
        db_table = "parcel"
        constraints = [
            models.UniqueConstraint(
                fields=["source_namespace", "source_record_id"], name="parcel_source_identity"
            ),
            models.CheckConstraint(
                condition=IsValid("geometry") & ~IsEmpty("geometry"),
                name="parcel_geometry_valid_nonempty",
            ),
            models.CheckConstraint(
                condition=models.Q(revision__gte=1), name="parcel_revision_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(source_namespace__regex=r"\S", source_record_id__regex=r"\S"),
                name="parcel_source_identity_nonblank",
            ),
            models.CheckConstraint(
                condition=models.Q(superseded_by__isnull=True)
                | ~models.Q(id=models.F("superseded_by")),
                name="parcel_supersession_not_self",
            ),
        ]

    def __str__(self):
        return self.code or str(self.id)


class MapIdentity(models.Model):
    """A provider identity, never an automatically accepted commercial identity."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_namespace = models.CharField(max_length=120)
    source_record_id = models.CharField(max_length=80)
    name = models.CharField(max_length=255, blank=True)
    name_ar = models.CharField(max_length=255, blank=True)
    kind = models.CharField(max_length=100, blank=True)
    revision = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["source_namespace", "source_record_id"],
                name="%(class)s_source_identity",
            ),
            models.CheckConstraint(
                condition=models.Q(revision__gte=1), name="%(class)s_revision_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(source_namespace__regex=r"\S", source_record_id__regex=r"\S"),
                name="%(class)s_source_nonblank",
            ),
            models.CheckConstraint(
                condition=IsValid("geometry") & ~IsEmpty("geometry"),
                name="%(class)s_geometry_valid",
            ),
        ]


class Street(MapIdentity):
    geometry = models.MultiLineStringField(srid=4326)

    class Meta(MapIdentity.Meta):
        db_table = "street"


class Building(MapIdentity):
    geometry = models.MultiPolygonField(srid=4326)
    height_m = models.FloatField(null=True)
    levels = models.PositiveSmallIntegerField(null=True)

    class Meta(MapIdentity.Meta):
        db_table = "building"
        constraints = [
            *MapIdentity.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(height_m__isnull=True)
                | models.Q(height_m__gt=0, height_m__lte=1000),
                name="building_height_range",
            ),
        ]


class Place(MapIdentity):
    geometry = models.PointField(srid=4326)

    class Meta(MapIdentity.Meta):
        db_table = "place"


class AdministrativeArea(MapIdentity):
    geometry = models.MultiPolygonField(srid=4326)
    superseded_by = models.ForeignKey(
        "self", null=True, on_delete=models.PROTECT, related_name="superseded_areas"
    )

    class Meta(MapIdentity.Meta):
        db_table = "administrative_area"
        constraints = [
            *MapIdentity.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(superseded_by__isnull=True)
                | ~models.Q(id=models.F("superseded_by")),
                name="administrative_area_supersession_not_self",
            ),
        ]
