"""Durable acquisition queue. Only Prefect acquires bytes; HTTP reads use the archive."""

import hashlib
import logging
import math
import struct
from datetime import timedelta

from django.db import connection, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from .basemap_models import PROVIDERS
from .history import audit_context
from .media_storage import read_capture
from .models import BasemapRequest, BasemapTile, Capture, IngestionRun, Source

logger = logging.getLogger(__name__)


def checked_tile(provider, z, x, y):
    if provider not in PROVIDERS or not 0 <= z <= 14 or not (0 <= x < 2**z and 0 <= y < 2**z):
        raise ValueError("Unregistered basemap tile")
    if provider != "openfreemap" and z < 8:
        raise ValueError("Sentinel zoom is outside its reviewed range")


def archived_tile(provider, z, x, y):
    checked_tile(provider, z, x, y)
    tile = (
        BasemapTile.objects.filter(
            request__provider=provider,
            request__z=z,
            request__x=x,
            request__y=y,
            capture__run__status__in=["succeeded", "quarantined", "running"],
        )
        .select_related("capture")
        .order_by("-capture__fetched_at", "-pk")
        .first()
    )
    if tile:
        return tile, read_capture(tile.capture, max_bytes=4 * 1024 * 1024)
    # Durable demand, never a provider request in a visitor's transaction.
    if BasemapRequest.objects.filter(available=False).count() < 5000:
        BasemapRequest.objects.get_or_create(provider=provider, z=z, x=x, y=y)
    return None


def seed_area(provider, bounds):
    """Reviewed coverage only; never prefetch the planet or silently exceed provider budgets."""
    west, south, east, north = bounds

    def coordinate(lon, lat, zoom):
        n = 2**zoom
        return int((lon + 180) / 360 * n), int(
            (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
        )

    rows = []
    for z in range(0 if provider == "openfreemap" else 8, 15):
        left, top = coordinate(west, north, z)
        right, bottom = coordinate(east, south, z)
        rows.extend(
            BasemapRequest(provider=provider, z=z, x=x, y=y)
            for x in range(left, right + 1)
            for y in range(top, bottom + 1)
        )
    if len(rows) > 1000:
        raise ValueError("Area exceeds the reviewed download budget")
    BasemapRequest.objects.bulk_create(rows, ignore_conflicts=True)
    return len(rows)


def validate_tile(provider, payload):
    if len(payload) > 4 * 1024 * 1024:
        raise ValueError("Tile byte budget exceeded")
    if provider != "openfreemap":
        if (
            len(payload) < 33
            or payload[:8] != b"\x89PNG\r\n\x1a\n"
            or payload[12:16] != b"IHDR"
            or struct.unpack(">II", payload[16:24]) != (256, 256)
        ):
            raise ValueError("Invalid PNG tile")
    elif payload and payload[0] != 0x1A:
        raise ValueError("Invalid vector tile envelope")


def archive_pending(
    provider, *, actor, acquire, run_key, limit=100, refresh=False, request_ids=None
):
    """Single runner, bounded batch, exact failure receipts and previous usable versions.

    acquire(request) returns Acquisition + provider version; transport lives in ingestion.
    No network request runs inside a database transaction.
    """
    if provider not in PROVIDERS or not 1 <= limit <= 100:
        raise ValueError("Invalid archive scope")
    source, _ = Source.objects.get_or_create(
        key=f"basemap:{provider}",
        defaults={
            "name": provider,
            "url": "https://openfreemap.org"
            if provider == "openfreemap"
            else "https://esa-worldcover.org/en/data-access",
        },
    )
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(8473301)")
        if not cursor.fetchone()[0]:
            return {"status": "busy", "saved": 0}
    try:
        # Owning the advisory lock proves no other archive process is active.
        # A killed worker may have committed valid tiles before its final marker.
        IngestionRun.objects.filter(source=source, status="running").update(
            status="quarantined", finished_at=timezone.now(), error="InterruptedArchiveBatch"
        )
        # Successful retries of the same Prefect task do not duplicate captures.
        previous = IngestionRun.objects.filter(
            source=source,
            actor=actor,
            connector_version=run_key,
            status__in=["succeeded", "quarantined"],
            error="",
        ).first()
        if previous:
            return previous.summary
        with audit_context(actor=actor):
            run = IngestionRun.objects.create(source=source, actor=actor, connector_version=run_key)
            now = timezone.now()
            pending = BasemapRequest.objects.filter(provider=provider)
            if request_ids is not None:
                pending = pending.filter(pk__in=request_ids)
            if not refresh:
                pending = pending.filter(
                    Q(available=False) | Q(last_attempt_at__lt=now - timedelta(days=7))
                )
            pending = pending.filter(
                Q(last_attempt_at__isnull=True) | Q(last_attempt_at__lt=now - timedelta(hours=1))
            )
            saved = failed = 0
            for request in pending.order_by("available", "last_attempt_at", "created_at", "pk")[
                :limit
            ]:
                acquired = None
                try:
                    # OpenFreeMap permits an area download up to 3000 tiles/50 MB.
                    # Count all retained versions, not merely the current batch.
                    if provider == "openfreemap":
                        used = (
                            BasemapTile.objects.filter(request__provider=provider).aggregate(
                                size=Sum("capture__byte_length")
                            )["size"]
                            or 0
                        )
                        if (
                            used >= 46 * 1024 * 1024
                            or BasemapTile.objects.filter(request__provider=provider).count()
                            >= 3000
                        ):
                            raise ValueError("OpenFreeMap offline archive budget exhausted")
                    acquired, version = acquire(request)
                    with transaction.atomic():
                        capture = Capture.objects.create(
                            run=run,
                            payload=acquired.payload,
                            byte_length=len(acquired.payload),
                            content_sha256=hashlib.sha256(acquired.payload).hexdigest(),
                            **acquired.capture_receipt(),
                        )
                        if acquired.http_status != 200:
                            failed += 1
                            request.last_error = f"HTTP{acquired.http_status}"
                        else:
                            try:
                                validate_tile(provider, acquired.payload)
                            except ValueError:
                                failed += 1
                                request.last_error = "InvalidTile"
                            else:
                                BasemapTile.objects.create(
                                    request=request,
                                    capture=capture,
                                    mime_type="application/x-protobuf"
                                    if provider == "openfreemap"
                                    else "image/png",
                                    provider_version=version,
                                    licence_code="ODbL-1.0"
                                    if provider == "openfreemap"
                                    else "CC-BY-4.0",
                                    attribution=(
                                        "OpenFreeMap · © OpenMapTiles · "
                                        "© OpenStreetMap contributors"
                                    )
                                    if provider == "openfreemap"
                                    else (
                                        f"© ESA WorldCover / Contains modified Copernicus "
                                        f"Sentinel data ({provider[-4:]}) processed by "
                                        "ESA WorldCover consortium · Terrascope"
                                    ),
                                )
                                request.available, request.last_error = True, ""
                                saved += 1
                except Exception as exc:
                    logger.warning("Basemap request %s failed", request.pk, exc_info=exc)
                    failed += 1
                    request.last_error = type(exc).__name__
                request.last_attempt_at = timezone.now()
                request.save(update_fields=["last_attempt_at", "last_error", "available"])
            metadata = getattr(acquire, "metadata", None)
            if metadata is not None:
                Capture.objects.create(
                    run=run,
                    payload=metadata.payload,
                    byte_length=len(metadata.payload),
                    content_sha256=metadata.sha256,
                    **metadata.capture_receipt(),
                )
            run.status = "quarantined" if failed else "succeeded"
            run.finished_at = timezone.now()
            run.summary = {
                "status": run.status,
                "saved": saved,
                "failed": failed,
                "provider": provider,
            }
            run.save(update_fields=["status", "finished_at", "summary"])
            # Successful bytes in a partial batch remain usable, never the failures.
            return run.summary
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(8473301)")
