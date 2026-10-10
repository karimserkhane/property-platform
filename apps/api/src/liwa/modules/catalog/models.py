import uuid

from django.contrib.gis.db import models


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
        constraints = [
            models.UniqueConstraint(
                fields=["source_namespace", "source_record_id"], name="parcel_source_identity"
            )
        ]

    def __str__(self):
        return self.code or str(self.id)
