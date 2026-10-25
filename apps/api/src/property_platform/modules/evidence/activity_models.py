"""Dated Sentinel-2 ground-change measurements of reviewed project parcels (B06).

A measurement compares two cloud-masked scenes of one parcel with one method version.
It is a signal of ground change, never a construction progress percentage. See
docs/engineering/CONSTRUCTION_ACTIVITY.md.
"""

from django.db import models

ACTIVITY_STATUSES = ("measured", "insufficient_clear_pixels")
ACTIVITY_LEVELS = ("low", "moderate", "high")


class ConstructionActivityMeasurement(models.Model):
    project = models.ForeignKey("catalog.Project", on_delete=models.PROTECT)
    parcel = models.ForeignKey("catalog.Parcel", on_delete=models.PROTECT)
    # The reviewed link that placed the project on this parcel when it was measured.
    identity_link = models.ForeignKey("evidence.ProjectIdentityLink", on_delete=models.PROTECT)
    run = models.ForeignKey("evidence.IngestionRun", on_delete=models.PROTECT)
    # Window captures of each date; their parent capture is the scene's STAC item.
    before_capture = models.ForeignKey(
        "evidence.Capture", on_delete=models.PROTECT, related_name="+"
    )
    after_capture = models.ForeignKey(
        "evidence.Capture", on_delete=models.PROTECT, related_name="+"
    )
    tile = models.CharField(max_length=20)
    before_scene_id = models.CharField(max_length=100)
    after_scene_id = models.CharField(max_length=100)
    before_acquired_at = models.DateTimeField()
    after_acquired_at = models.DateTimeField()
    method_version = models.CharField(max_length=40)
    status = models.CharField(max_length=30)
    parcel_pixels = models.PositiveIntegerField()
    clear_pixels = models.PositiveIntegerField()
    changed_pixels = models.PositiveIntegerField(null=True)
    changed_share = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    median_difference = models.DecimalField(max_digits=6, decimal_places=4, null=True)
    level = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "construction_activity_measurement"
        constraints = [
            models.UniqueConstraint(
                fields=["parcel", "before_scene_id", "after_scene_id", "method_version"],
                name="construction_activity_one_per_pair",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    tile__regex=r"^MGRS-[0-9]{2}[A-Z]{3}$",
                    before_scene_id__regex=r"^S2[ABC]_[0-9]{2}[A-Z]{3}_[0-9]{8}_[0-9]+_L2A$",
                    after_scene_id__regex=r"^S2[ABC]_[0-9]{2}[A-Z]{3}_[0-9]{8}_[0-9]+_L2A$",
                    method_version__regex=r"^sentinel-activity-v[1-9][0-9]*$",
                    after_acquired_at__gt=models.F("before_acquired_at"),
                    parcel_pixels__gte=1,
                    clear_pixels__lte=models.F("parcel_pixels"),
                ),
                name="construction_activity_scenes_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status="insufficient_clear_pixels",
                    changed_pixels__isnull=True,
                    changed_share__isnull=True,
                    median_difference__isnull=True,
                    level="",
                )
                | models.Q(
                    status="measured",
                    clear_pixels__gte=1,
                    changed_pixels__isnull=False,
                    changed_pixels__lte=models.F("clear_pixels"),
                    changed_share__gte=0,
                    changed_share__lte=1,
                    median_difference__gte=0,
                    level__in=ACTIVITY_LEVELS,
                ),
                name="construction_activity_result_valid",
            ),
        ]
