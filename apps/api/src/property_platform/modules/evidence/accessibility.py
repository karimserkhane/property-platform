"""Read archived walking analysis; only Prefect acquires inputs and computes new versions."""

import hashlib
import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from .history import audit_context
from .media_storage import read_capture
from .models import (
    Capture,
    IngestionRun,
    RoutingGraph,
    RoutingGraphPart,
    Source,
    WalkingArea,
    WalkingRequest,
)

GRAPH_URL = "https://download.geofabrik.de/asia/gcc-states-latest.osm.pbf"
ENGINE_VERSION = "valhalla-3.9.1/618cad5eb/graph-v1"


class StoredGraphReceipt:
    """Replay exact archived bytes and original acquisition times, never a fresh source claim."""

    def __init__(self, graph):
        self.graph = graph
        self.sha256 = graph.sha256
        manifest = json.loads(read_capture(graph.capture, max_bytes=4096))
        self.byte_length = manifest["byte_length"]
        self.http_status = 200

    def chunks(self):
        offset = 0
        for sequence, part in enumerate(
            self.graph.parts.select_related("capture").order_by("sequence").iterator(chunk_size=1)
        ):
            if part.sequence != sequence or part.offset_bytes != offset:
                raise ValueError("ArchivedGraphSequenceMismatch")
            payload = read_capture(part.capture, max_bytes=4 * 1024 * 1024)
            if hashlib.sha256(payload).hexdigest() != part.capture.content_sha256:
                raise ValueError("ArchivedGraphPartHashMismatch")
            offset += len(payload)
            yield payload
        if offset != self.byte_length:
            raise ValueError("ArchivedGraphIncomplete")


def walking_scope(longitude, latitude, minutes):
    lon, lat = Decimal(str(longitude)), Decimal(str(latitude))
    if (
        not lon.is_finite()
        or not lat.is_finite()
        or not (51 <= lon <= 57 and 22 <= lat <= 27)
        or minutes not in (5, 10, 15)
    ):
        raise ValueError("Invalid walking scope")
    return lon.quantize(Decimal("0.00001")), lat.quantize(Decimal("0.00001")), minutes


def walking_area(longitude, latitude, minutes):
    lon, lat, minutes = walking_scope(longitude, latitude, minutes)
    request = WalkingRequest.objects.filter(longitude=lon, latitude=lat, minutes=minutes).first()
    if request is None:
        if WalkingRequest.objects.count() >= 5000:
            return None
        with audit_context(actor="preview-walking-request"):
            request, _ = WalkingRequest.objects.get_or_create(
                longitude=lon, latitude=lat, minutes=minutes
            )
    version = (
        request.versions.filter(
            graph__ready=True, capture__run__status__in=["succeeded", "quarantined"]
        )
        .select_related("graph__capture", "capture")
        .order_by("-graph__ingested_at", "-ingested_at")
        .first()
    )
    if version is None:
        return None
    latest = RoutingGraph.objects.filter(ready=True).order_by("-ingested_at").first()
    return {
        "collection": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(version.geometry.geojson),
                    "properties": {"minutes": minutes, "mode": "pedestrian"},
                }
            ],
        },
        "ingested_at": version.ingested_at,
        "graph_id": version.graph.sha256,
        "graph_fetched_at": version.graph.capture.fetched_at,
        "source_url": version.graph.capture.url,
        "historical": latest is not None and version.graph_id != latest.pk,
    }


def archive_graph(*, actor, acquire, build, run_key, from_history=False):
    source, _ = Source.objects.get_or_create(
        key="routing-geofabrik-gcc",
        defaults={"name": "OpenStreetMap / Geofabrik GCC routing extract", "url": GRAPH_URL},
    )
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(8473302)")
        if not cursor.fetchone()[0]:
            return {"status": "succeeded", "summary": {"busy": True}}
    try:
        with audit_context(actor=actor):
            IngestionRun.objects.filter(source=source, status="running").update(
                status="quarantined", finished_at=timezone.now(), error="InterruptedGraphBuild"
            )
            run = IngestionRun.objects.create(source=source, actor=actor, connector_version=run_key)
            try:
                # Retain earlier versions; stop at the reviewed archive budget.
                stored = (
                    RoutingGraph.objects.select_related("capture").order_by("-ingested_at").first()
                )
                if from_history and stored is None:
                    raise ValueError("NoArchivedGraph")
                acquired = StoredGraphReceipt(stored) if from_history else acquire()
                if acquired.http_status != 200:
                    raise ValueError("GraphAcquisitionFailed")
                graph = RoutingGraph.objects.filter(sha256=acquired.sha256).first()
                if graph is None:
                    if RoutingGraph.objects.count() >= 12:
                        raise ValueError("GraphArchiveBudgetReached")
                    manifest = json.dumps(
                        {
                            "format": "osm-pbf-chunks-v1",
                            "sha256": acquired.sha256,
                            "byte_length": acquired.byte_length,
                            "chunk_size": 4 * 1024 * 1024,
                        },
                        sort_keys=True,
                    ).encode()
                    capture = Capture.objects.create(
                        run=run,
                        payload=manifest,
                        byte_length=len(manifest),
                        content_sha256=hashlib.sha256(manifest).hexdigest(),
                        acquisition_method="routing_source_manifest",
                        **acquired.capture_receipt(),
                    )
                    graph = RoutingGraph.objects.create(
                        sha256=acquired.sha256, capture=capture, engine_version=ENGINE_VERSION
                    )
                digest, offset = hashlib.sha256(), 0
                for sequence, chunk in enumerate(acquired.chunks()):
                    if len(chunk) > 4 * 1024 * 1024:
                        raise ValueError("GraphPartBudgetExceeded")
                    digest.update(chunk)
                    part_sha = hashlib.sha256(chunk).hexdigest()
                    existing = (
                        graph.parts.filter(sequence=sequence).select_related("capture").first()
                    )
                    if existing is not None:
                        if (
                            existing.offset_bytes != offset
                            or existing.capture.content_sha256 != part_sha
                        ):
                            raise ValueError("GraphPartMismatch")
                    else:
                        with transaction.atomic():
                            part_capture = Capture.objects.create(
                                run=run,
                                parent_capture=graph.capture,
                                payload=chunk,
                                byte_length=len(chunk),
                                content_sha256=part_sha,
                                acquisition_method="regional_osm_chunk",
                                **acquired.capture_receipt(),
                            )
                            RoutingGraphPart.objects.create(
                                graph=graph,
                                capture=part_capture,
                                sequence=sequence,
                                offset_bytes=offset,
                            )
                    offset += len(chunk)
                if digest.hexdigest() != acquired.sha256 or offset != acquired.byte_length:
                    raise ValueError("GraphReconstructionMismatch")
                build(graph.sha256, parts=acquired.chunks())
                graph.ready = True
                graph.save(update_fields=["ready"])
                run.status = "succeeded"
                run.summary = {
                    "sha256": graph.sha256,
                    "bytes": acquired.byte_length,
                    "engine_version": graph.engine_version,
                }
            except Exception as exc:
                run.status, run.error = "failed", type(exc).__name__
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "error", "summary", "finished_at"])
            return {"status": run.status, "summary": run.summary, "error": run.error}
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(8473302)")


def archive_walking(*, actor, compute, run_key):
    graph = RoutingGraph.objects.filter(ready=True).order_by("-ingested_at").first()
    if graph is None:
        return {"status": "succeeded", "summary": {"graph_ready": False, "saved": 0}}
    source, _ = Source.objects.get_or_create(
        key="walking-analysis",
        defaults={
            "name": "Walking areas computed from archived OSM",
            "url": "https://valhalla.github.io/valhalla/api/isochrone/api-reference/",
        },
    )
    with audit_context(actor=actor):
        run = IngestionRun.objects.create(source=source, actor=actor, connector_version=run_key)
        now = timezone.now()
        pending = WalkingRequest.objects.exclude(versions__graph=graph).filter(
            Q(last_attempt_at__isnull=True) | Q(last_attempt_at__lt=now - timedelta(minutes=5))
        )
        saved = failed = 0
        for request in pending.order_by("created_at")[:10]:
            started = timezone.now()
            try:
                value = compute(request, graph.sha256)
                payload = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
                if (
                    len(payload) > 2 * 1024 * 1024
                    or value.get("type") != "FeatureCollection"
                    or len(value.get("features", [])) != 1
                ):
                    raise ValueError("InvalidWalkingResponse")
                geometry = GEOSGeometry(json.dumps(value["features"][0]["geometry"]), srid=4326)
                if geometry.geom_type == "Polygon":
                    geometry = MultiPolygon(geometry, srid=4326)
                if geometry.geom_type != "MultiPolygon" or not geometry.valid or geometry.empty:
                    raise ValueError("InvalidWalkingGeometry")
                with transaction.atomic():
                    capture = Capture.objects.create(
                        run=run,
                        parent_capture=graph.capture,
                        url=source.url,
                        payload=payload,
                        byte_length=len(payload),
                        content_sha256=hashlib.sha256(payload).hexdigest(),
                        fetched_started_at=started,
                        fetched_at=timezone.now(),
                        http_status=200,
                        acquisition_method="local_routing_computation",
                        timestamp_basis="computation_clock",
                    )
                    WalkingArea.objects.get_or_create(
                        request=request,
                        graph=graph,
                        defaults={"capture": capture, "geometry": geometry},
                    )
                request.last_error = ""
                saved += 1
            except Exception as exc:
                request.last_error = type(exc).__name__
                failed += 1
            request.last_attempt_at = timezone.now()
            request.save(update_fields=["last_attempt_at", "last_error"])
        run.status = "quarantined" if failed else "succeeded"
        run.finished_at = timezone.now()
        run.summary = {"saved": saved, "failed": failed, "graph": graph.sha256}
        run.save(update_fields=["status", "summary", "finished_at"])
        return {"status": run.status, "summary": run.summary}
