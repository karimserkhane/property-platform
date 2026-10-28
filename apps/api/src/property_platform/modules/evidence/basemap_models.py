"""Typed basemap queue and immutable tile versions; no arbitrary source URLs."""

from django.db import models

PROVIDERS = ("openfreemap", "sentinel-worldcover-2020", "sentinel-worldcover-2021")


class BasemapRequest(models.Model):
    provider = models.CharField(max_length=40)
    z = models.PositiveSmallIntegerField()
    x = models.PositiveIntegerField()
    y = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_attempt_at = models.DateTimeField(null=True)
    last_error = models.CharField(max_length=100, blank=True)
    available = models.BooleanField(default=False)

    class Meta:
        db_table = "basemap_request"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "z", "x", "y"], name="basemap_request_tile_key"
            ),
            models.CheckConstraint(
                condition=models.Q(provider__in=PROVIDERS, z__lte=14, x__lt=16384, y__lt=16384),
                name="basemap_request_bounds",
            ),
        ]


class BasemapTile(models.Model):
    request = models.ForeignKey(BasemapRequest, on_delete=models.PROTECT, related_name="versions")
    capture = models.OneToOneField("evidence.Capture", on_delete=models.PROTECT)
    mime_type = models.CharField(max_length=80)
    licence_code = models.CharField(max_length=40)
    attribution = models.CharField(max_length=500)
    provider_version = models.CharField(max_length=160)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "basemap_tile"
