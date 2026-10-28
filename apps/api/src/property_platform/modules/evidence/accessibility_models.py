"""Versioned routing inputs and derived walking polygons, separate from cadastral identity."""

from django.contrib.gis.db import models as gis
from django.db import models


class RoutingGraph(models.Model):
    sha256 = models.CharField(max_length=64, unique=True)
    capture = models.OneToOneField("evidence.Capture", on_delete=models.PROTECT)
    engine_version = models.CharField(max_length=160)
    ready = models.BooleanField(default=False)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "routing_graph"


class WalkingRequest(models.Model):
    longitude = models.DecimalField(max_digits=9, decimal_places=5)
    latitude = models.DecimalField(max_digits=8, decimal_places=5)
    minutes = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_attempt_at = models.DateTimeField(null=True)
    last_error = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "walking_request"
        constraints = [
            models.UniqueConstraint(
                fields=["longitude", "latitude", "minutes"], name="walking_request_scope"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    minutes__in=[5, 10, 15],
                    longitude__gte=51,
                    longitude__lte=57,
                    latitude__gte=22,
                    latitude__lte=27,
                ),
                name="walking_request_bounds",
            ),
        ]


class RoutingGraphPart(models.Model):
    graph = models.ForeignKey(RoutingGraph, on_delete=models.PROTECT, related_name="parts")
    capture = models.OneToOneField("evidence.Capture", on_delete=models.PROTECT)
    sequence = models.PositiveSmallIntegerField()
    offset_bytes = models.PositiveBigIntegerField()
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "routing_graph_part"
        constraints = [
            models.UniqueConstraint(
                fields=["graph", "sequence"], name="routing_graph_part_sequence"
            )
        ]


class WalkingArea(models.Model):
    request = models.ForeignKey(WalkingRequest, on_delete=models.PROTECT, related_name="versions")
    graph = models.ForeignKey(RoutingGraph, on_delete=models.PROTECT)
    capture = models.OneToOneField("evidence.Capture", on_delete=models.PROTECT)
    geometry = gis.MultiPolygonField(srid=4326)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "walking_area"
        constraints = [
            models.UniqueConstraint(fields=["request", "graph"], name="walking_area_graph_version")
        ]
