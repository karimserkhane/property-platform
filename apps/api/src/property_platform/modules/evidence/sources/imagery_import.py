"""Inert historical raster receipts; rendering stays outside the API runtime."""

import base64
import hashlib
import json
import struct
from datetime import datetime

from django.db import connection, transaction
from django.utils import timezone

from ..models import Capture, ImageryScene, IngestionRun, Source

BBOX = [54.3887, 24.4708, 54.4271, 24.5175]
SCENES = {"S2C_40RBN_20261004_0_L2A", "S2C_40RBN_20260629_0_L2A"}
BASE = "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/"


def validate(row):
    payload = base64.b64decode(row["payload"], validate=True)
    png = base64.b64decode(row["preview"], validate=True)
    item = json.loads(payload)
    started = datetime.fromisoformat(row["fetched_started_at"])
    fetched = datetime.fromisoformat(row["fetched_at"])
    acquired = datetime.fromisoformat(item["properties"]["datetime"].replace("Z", "+00:00"))
    asset = item["assets"]["visual"]["href"]
    cloud = float(item["properties"]["eo:cloud_cover"])
    if (
        item["id"] not in SCENES
        or row["url"] != BASE + item["id"]
        or row["bbox"] != BBOX
        or row["render_version"] != "reem-sentinel-crop-v1"
        or not asset.startswith("https://sentinel-cogs.s3.us-west-2.amazonaws.com/")
        or not 0 <= cloud <= 100
        or not started.tzinfo
        or not fetched.tzinfo
        or not acquired.tzinfo
        or not acquired <= fetched <= timezone.now()
        or not started <= fetched
        or len(payload) > 1024 * 1024
        or len(png) > 4 * 1024 * 1024
        or png[:8] != b"\x89PNG\r\n\x1a\n"
        or png[12:16] != b"IHDR"
        or not all(1 <= size <= 768 for size in struct.unpack(">II", png[16:24]))
        or hashlib.sha256(png).hexdigest() != row["preview_sha256"]
    ):
        raise ValueError("Invalid imagery receipt")
    return item, payload, png, started, fetched, acquired, asset, cloud


def import_imagery(rows, *, actor):
    if not actor.strip() or len(actor) > 160:
        raise ValueError("Valid actor required")
    if not isinstance(rows, list) or len(rows) != 2:
        raise ValueError("Two scenes required")
    values = [validate(row) for row in rows]
    if {value[0]["id"] for value in values} != SCENES:
        raise ValueError("Duplicate scenes")
    output = []
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(716548220)")
        for row, value in zip(rows, values, strict=True):
            item, payload, png, started, fetched, acquired, asset, cloud = value
            source, _ = Source.objects.get_or_create(
                key="sentinel:" + item["id"],
                defaults={"name": "Copernicus Sentinel-2 / Earth Search", "url": row["url"]},
            )
            run = IngestionRun.objects.create(
                source=source, actor=actor.strip(), connector_version=row["render_version"]
            )
            capture = Capture.objects.create(
                run=run,
                url=row["url"],
                payload=payload,
                byte_length=len(payload),
                content_sha256=hashlib.sha256(payload).hexdigest(),
                http_status=200,
                fetched_started_at=started,
                fetched_at=fetched,
                acquisition_method="isolated_worker_receipt",
                timestamp_basis="collector_clock",
            )
            scene, created = ImageryScene.objects.get_or_create(
                scene_id=item["id"],
                defaults={
                    "capture": capture,
                    "acquired_at": acquired,
                    "cloud_cover_tile": cloud,
                    "west": BBOX[0],
                    "south": BBOX[1],
                    "east": BBOX[2],
                    "north": BBOX[3],
                    "preview_png": png,
                    "preview_sha256": row["preview_sha256"],
                    "asset_url": asset,
                    "render_version": row["render_version"],
                },
            )
            if not created and scene.preview_sha256 != row["preview_sha256"]:
                raise ValueError("Existing scene preview differs; review before replacement")
            run.status, run.finished_at = "succeeded", timezone.now()
            run.summary = {"scene": scene.scene_id, "created": created}
            run.save(update_fields=["status", "finished_at", "summary"])
            output.append(run)
    return output
