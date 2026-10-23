"""Bounded one-off OSM API acquisition. Original XML is retained, never fake Overpass JSON."""

import hashlib
import json

from django.db import connection

from .collection_profiles import collection_for
from .map_import import LOCK_KEY, materialize_map_records, osm_data_records
from .models import Capture, IngestionRun, Source
from .onwani import SourceError
from .osm_api_protocol import URL, VERSION, boxes, decode
from .runs import mark_failed


def import_bootstrap(*, territory, actor, acquisition):
    profile = collection_for(territory)
    queries = boxes(territory)
    if connection.vendor != "postgresql":
        raise ValueError("OSM bootstrap requires PostGIS")
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [LOCK_KEY])
        if not cursor.fetchone()[0]:
            raise ValueError("Map acquisition already running")
    run = None
    try:
        source, _ = Source.objects.get_or_create(
            key=profile.map_namespace("osm"),
            defaults={
                "name": f"OpenStreetMap — {profile.name} (ODbL)",
                "url": URL,
            },
        )
        run = IngestionRun.objects.create(source=source, actor=actor, connector_version=VERSION)
        staged, rejected, identities, size = [], [], {}, 0
        for params in queries:
            payload, receipt = acquisition(URL, params)
            size += len(payload)
            if size > 64 * 1024 * 1024:
                raise SourceError("OSM bootstrap exceeds its aggregate budget")
            capture = Capture.objects.create(
                run=run,
                payload=payload,
                byte_length=len(payload),
                content_sha256=hashlib.sha256(payload).hexdigest(),
                **receipt,
            )
            if receipt["http_status"] != 200:
                raise SourceError("OSM API returned non-success status")
            data = decode(payload)
            unique = []
            for row in data["elements"]:
                identity = (row["type"], row["id"])
                digest = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
                if identity in identities:
                    if identities[identity] != digest:
                        raise SourceError("OSM object changed between windows")
                    continue
                identities[identity] = digest
                unique.append(row)
            if unique:
                rows, errors = osm_data_records(
                    {**data, "elements": unique}, capture, territory=territory, xml_snapshot=True
                )
                staged.extend(rows)
                rejected.extend(errors)
        return materialize_map_records(
            run, profile.map_namespace("osm"), staged, rejected, actor=actor
        )
    except Exception as exc:
        if run:
            mark_failed(run, exc)
        raise
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [LOCK_KEY])
