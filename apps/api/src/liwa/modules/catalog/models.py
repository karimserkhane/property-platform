import uuid

from django.contrib.gis.db import models
from django.contrib.gis.db.models.functions import IsEmpty, IsValid


class Parcel(models.Model):
    """Source-reconciled catalogue identity, not an automatically published dossier."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_namespace = models.CharField(max_length=120)
    source_record_id = models.CharField(max_length=80)
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
        ]

    def __str__(self):
        return self.code or str(self.id)
