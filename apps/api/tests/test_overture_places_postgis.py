"""Real PostGIS: evidence, source isolation, filtering, replay and public map visibility."""

import copy
import hashlib
import json
import os
from datetime import UTC, datetime

import pytest
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Overture requires real PostGIS", allow_module_level=True)

from django.contrib.gis.geos import Point  # noqa: E402
from test_reem_map_postgis import district  # noqa: E402

from property_platform.modules.catalog.models import Place  # noqa: E402
from property_platform.modules.evidence.maps import overture_places as protocol  # noqa: E402
from property_platform.modules.evidence.models import Capture, MapObservation  # noqa: E402
from property_platform.modules.evidence.rebuild.orchestration import execute_import  # noqa: E402
from property_platform.modules.publication.place_display import distinct_places  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def row(identity="example", *, x=54.4, y=24.5):
    return {
        "id": identity,
        "names": {"primary": "Neighbourhood Cafe", "common": {"ar": "مقهى"}},
        "taxonomy": {"primary": "coffee_shop", "hierarchy": ["food_and_drink", "cafe"]},
        "confidence": 0.95,
        "operating_status": "open",
        "sources": [{"dataset": "meta", "license": "CDLA-Permissive-2.0"}],
        "bbox": {"xmin": x, "xmax": x, "ymin": y, "ymax": y},
        "geometry_wkb": Point(x, y, srid=4326).wkb.hex(),
    }


def execute(rows, identity="first"):
    payload = json.dumps(
        {
            "release": protocol.RELEASE,
            "territory": "al-reem-island",
            "bounds": [54.3886, 24.4707, 54.4273, 24.5177],
            "rows": rows,
        }
    ).encode()
    now = datetime.now(UTC)
    receipt = {
        "url": protocol.URL,
        "fetched_started_at": now,
        "fetched_at": now,
        "http_status": 200,
        "etag": "",
        "last_modified_raw": "",
        "acquisition_method": "overture_parquet_extract",
        "timestamp_basis": "collector_clock",
    }
    return execute_import(
        operation="map",
        scope="al-reem-island:overture",
        actor="test",
        execution_key=hashlib.sha256(identity.encode()).hexdigest(),
        acquisition=lambda base, params: (payload, receipt),
    )


def test_evidence_idempotency_and_both_map_and_surroundings_scope(client):
    district()
    assert execute([row()])["status"] == "succeeded"
    obj = Place.objects.get()
    assert obj.kind == "cafe" and obj.name_ar == "مقهى"
    assert execute([row()], "second")["summary"]["unchanged"] == 1
    assert Place.objects.count() == 1
    assert MapObservation.objects.count() == 2 and Capture.objects.count() == 2
    assert MapObservation.objects.first().source_published_at is None
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get(
            "/api/v1/preview/map-context",
            {
                "territory": "al-reem-island",
                "bbox": "54.39,24.49,54.42,24.52",
            },
        )
    assert response.status_code == 200
    places = response.json()["place"]["features"]
    assert len(places) == 1
    assert places[0]["properties"]["use_types"] == ["cafe"]
    assert places[0]["properties"]["source"]["reliability"] == "community"


def test_closed_low_confidence_and_outside_district_are_not_published():
    district()
    low, closed, outside = row("low"), row("closed"), row("outside", x=54.48)
    low["confidence"] = 0.2
    closed["operating_status"] = "permanently_closed"
    result = execute([row(), low, closed, outside])
    assert result["status"] == "succeeded" and Place.objects.count() == 1


def test_invalid_geometry_is_quarantined_and_duplicate_snapshot_rolls_back():
    district()
    invalid = row("invalid")
    invalid["geometry_wkb"] = "invalid"
    assert execute([row(), invalid])["status"] == "quarantined"
    duplicate = copy.deepcopy(row())
    assert execute([row(), duplicate], "duplicate")["status"] == "failed"
    assert Place.objects.count() == 1 and Capture.objects.count() == 2


def test_display_dedup_does_not_hide_different_branches_or_merge_sources():
    def feature(identity, namespace, x):
        return {
            "id": identity,
            "name": "Cafe",
            "kind": "cafe",
            "source_namespace": namespace,
            "geometry": {"type": "Point", "coordinates": [x, 24.5]},
        }

    osm = feature("osm", "osm:reem:osm", 54.4)
    duplicate = feature("overture", "overture:reem:places", 54.40001)
    branch = feature("branch", "overture:reem:places", 54.401)
    assert distinct_places([duplicate, osm, branch]) == [osm, branch]
