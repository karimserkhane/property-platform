"""Reviewed Overture extract protocol; no network or analytical engine in the API."""

import hashlib
import math

from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos.error import GEOSException
from django.utils import timezone

from property_platform.modules.catalog.models import AdministrativeArea

from .collection_profiles import collection_for
from .map_import import materialize_map_records
from .models import Capture, IngestionRun, Source
from .onwani import SourceError
from .overture_protocol import MIN_CONFIDENCE, RELEASE, URL, VERSION, decode, namespace, place_kind


def records(rows, capture, district):
    staged, rejected, seen = [], [], set()
    for row in rows:
        identity = row.get("id") if isinstance(row, dict) else None
        if not isinstance(identity, str) or not 1 <= len(identity) <= 100 or identity in seen:
            raise SourceError("Missing or duplicate Overture identity")
        seen.add(identity)
        try:
            names = row["names"]
            name = names["primary"]
            if not isinstance(name, str) or not 1 <= len(name.strip()) <= 255:
                raise ValueError("Invalid place name")
            confidence = row.get("confidence")
            if type(confidence) not in (int, float) or not math.isfinite(confidence):
                raise ValueError("Missing confidence")
            if not 0 <= confidence <= 1:
                raise ValueError("Invalid confidence")
            if confidence < MIN_CONFIDENCE or row.get("operating_status") in {
                "permanently_closed",
                "temporarily_closed",
                "closed",
            }:
                continue
            box = row["bbox"]
            coordinates = [box[key] for key in ("xmin", "ymin", "xmax", "ymax")]
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in coordinates):
                raise ValueError("Invalid place coordinates")
            x, y, xmax, ymax = coordinates
            if abs(xmax - x) > 0.00001 or abs(ymax - y) > 0.00001:
                raise ValueError("Expected point bounds")
            point = GEOSGeometry(memoryview(bytes.fromhex(row["geometry_wkb"])), srid=4326)
            if point.geom_type != "Point" or point.empty or not point.valid:
                raise ValueError("Expected valid place point")
            if not x <= point.x <= xmax or not y <= point.y <= ymax:
                raise ValueError("Place point outside declared bounds")
            if not district.covers(point):
                continue
            if not isinstance(row.get("sources"), list) or not row["sources"]:
                raise ValueError("Missing upstream provenance")
            common = dict(names.get("common") or {})
            arabic = common.get("ar", "")
            if not isinstance(arabic, str) or len(arabic) > 255:
                raise ValueError("Invalid Arabic name")
            kind = place_kind(row)
            staged.append(
                (
                    "place",
                    identity,
                    {"name": name.strip(), "name_ar": arabic, "kind": kind},
                    point,
                    {
                        **row,
                        "release": RELEASE,
                        "license_url": "https://docs.overturemaps.org/attribution/",
                    },
                    capture,
                    f"https://explore.overturemaps.org/?id={identity}",
                    None,
                )
            )
        except ValueError, KeyError, TypeError, AttributeError, GEOSException:
            rejected.append((identity, row, capture))
    return staged, rejected


def import_places(*, territory, actor, acquisition):
    profile = collection_for(territory)
    source, _ = Source.objects.get_or_create(
        key=namespace(territory),
        defaults={
            "name": f"Overture Maps Places — {profile.name} (CDLA / Apache / CC0)",
            "url": URL,
        },
    )
    run = IngestionRun.objects.create(source=source, actor=actor, connector_version=VERSION)
    try:
        payload, receipt = acquisition(URL, {})
        capture = Capture.objects.create(
            run=run,
            payload=payload,
            byte_length=len(payload),
            content_sha256=hashlib.sha256(payload).hexdigest(),
            **receipt,
        )
        if receipt["http_status"] != 200:
            raise SourceError("Overture acquisition failed")
        rows = decode(payload, territory)
        district = AdministrativeArea.objects.get(
            active=True,
            kind="district",
            name=profile.district_name,
            source_namespace=profile.map_namespace("district"),
            superseded_by__isnull=True,
        ).geometry
        staged, rejected = records(rows, capture, district)
        materialize_map_records(
            run,
            namespace(territory),
            staged,
            rejected,
            actor=actor,
            quarantine_reason="Invalid Overture place geometry, name or provenance; not repaired",
        )
        run.summary.update(
            source_records=len(rows),
            excluded=len(rows) - len(staged) - len(rejected),
            release=RELEASE,
        )
        run.save(update_fields=["summary"])
        return run
    except Exception as exc:
        run.status, run.error, run.finished_at = "failed", type(exc).__name__, timezone.now()
        run.save(update_fields=["status", "error", "finished_at"])
        raise
