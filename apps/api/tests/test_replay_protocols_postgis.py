"""Legacy Onwani/Overpass requests are reissued exactly, recorded, and never guessed."""

import hashlib
import json
import os
from datetime import UTC, datetime
from urllib.parse import urlencode
from uuid import uuid4

import pytest

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Capture rebuild requires real PostGIS", allow_module_level=True)

from django.contrib.gis.geos import MultiPolygon, Polygon  # noqa: E402

from property_platform.modules.catalog.models import (  # noqa: E402
    AdministrativeArea,
    Building,
    Parcel,
)
from property_platform.modules.evidence import map_sources, onwani  # noqa: E402
from property_platform.modules.evidence import rebuild_archive as archive  # noqa: E402
from property_platform.modules.evidence import replay_protocols as legacy  # noqa: E402
from property_platform.modules.evidence.collection_profiles import collection_for  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    IngestionRun,
    MapObservation,
    ParcelObservation,
)

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

REEM = "al-reem-island"
# Copied from the archived 11 October 2026 receipts of runs 9d04f812 and d7b5f4bc.
V1_FIELDS = (
    "OBJECTID,PLOTID,GISID,SectorNumber_PlotID,DISTRICTENG,DISTRICTID,MUNICIPALITYENG,"
    "COMMUNITYENG,ELMS_LandUse_Const,Construction_Status,APPROVALDATE,MODIFIEDDATE,"
    "DataReceivedDate,Permit_LastDate,Permit_LastType,MEPS_CONS_STATUS,MEPS_CONS_UPDATEON,"
    "DMT_DCR_URL"
)
BBOX = "(24.4707,54.3886,24.5177,54.4273)"
NAMED_POI_QUERY = (
    f"[out:json][timeout:45];(way[building]{BBOX};way[highway][name]{BBOX};"
    f"nwr[name][amenity]{BBOX};nwr[name][leisure]{BBOX};nwr[name][building]{BBOX};"
    ");out meta center geom;"
)


def captured(root, value, url):
    payload = json.dumps(value).encode()
    digest = hashlib.sha256(payload).hexdigest()
    (root / "blobs").mkdir(exist_ok=True)
    (root / "blobs" / digest).write_bytes(payload)
    stamp = datetime(2026, 10, 11, tzinfo=UTC).isoformat()
    return {
        "sha256": digest,
        "byte_length": len(payload),
        "receipt": {
            "url": url,
            "fetched_at": stamp,
            "fetched_started_at": stamp,
            "http_status": 200,
            "acquisition_method": "scheduled_https_collect",
            "timestamp_basis": "collector_clock",
        },
    }


def manifest(root, step, expected):
    archive.write_json(
        root / "manifest.json",
        {
            "version": 1,
            "snapshot_at": "2026-10-23T00:00:00+00:00",
            "expected": {**archive.counts(), **expected},
            "steps": [step],
            "scenes": [],
            "tiles": [],
            "omitted": [],
        },
    )


def onwani_v1_captures(root):
    where = collection_for(REEM).parcel_where
    listing = {"objectIds": [1]}
    feature = {
        "attributes": {
            "OBJECTID": 1,
            "DISTRICTENG": "AL REEM ISLAND",
            "MUNICIPALITYENG": "ADM",
            "SectorNumber_PlotID": "RT1_C1",
            "ELMS_LandUse_Const": "Residential",
        },
        "geometry": {"rings": [[[54.4, 24.5], [54.41, 24.5], [54.4, 24.51], [54.4, 24.5]]]},
    }
    ids = "/query?" + urlencode({"f": "json", "where": where, "returnIdsOnly": "true"})
    batch = {
        "f": "json",
        "where": where,
        "objectIds": "1",
        "outFields": V1_FIELDS,
        "returnGeometry": "true",
        "outSR": "4326",
    }
    metadata = {
        "name": "PLOT",
        "geometryType": "esriGeometryPolygon",
        "extent": {"spatialReference": {"wkid": 4326}},
        "fields": [{"name": f} for f in onwani.FIELDS.split(",")],
    }
    return [
        captured(root, value, onwani.BASE_URL + suffix)
        for value, suffix in (
            (metadata, "?f=pjson"),
            (listing, ids),
            (
                {"features": [feature], "spatialReference": {"wkid": 4326}},
                "/query?" + urlencode(batch),
            ),
            (listing, ids),
        )
    ]


def overpass_captures(root):
    data = {
        "osm3s": {"timestamp_osm_base": "2026-10-11T00:00:00Z"},
        "elements": [
            {
                "type": "way",
                "id": 1,
                "timestamp": "2026-01-01T00:00:00Z",
                "version": 1,
                "tags": {"building": "apartments"},
                "geometry": [
                    {"lon": lon, "lat": lat}
                    for lon, lat in [(54.4, 24.5), (54.401, 24.5), (54.401, 24.501), (54.4, 24.5)]
                ],
            }
        ],
    }
    url = map_sources.OSM_URL + "?" + urlencode({"data": NAMED_POI_QUERY})
    return [captured(root, data, url)]


def test_registry_lists_only_versions_whose_requests_differ():
    assert legacy.ONWANI_FIELDS["onwani-reem-v1"] == V1_FIELDS
    assert legacy.named_poi_osm_query(REEM) == NAMED_POI_QUERY
    assert legacy.named_poi_osm_query(REEM) != collection_for(REEM).osm_query
    assert legacy.historical_protocol("onwani", REEM, "onwani-reem-v1").onwani_fields
    for version in ("onwani-reem-v2", "onwani-reem-v3", onwani.VERSION, "", "unknown"):
        assert legacy.historical_protocol("onwani", REEM, version) is None
    assert legacy.historical_protocol("map", f"{REEM}:osm", "reem-map-v2").osm_query
    assert legacy.historical_protocol("map", f"{REEM}:district", "reem-map-v2") is None
    assert legacy.historical_protocol("map", f"{REEM}:osm", map_sources.VERSION) is None
    assert legacy.historical_protocol("sdi_parcels", REEM, "onwani-reem-v1") is None


def test_onwani_v1_receipts_replay_with_their_own_fields_and_current_mapping(tmp_path):
    step = {
        "operation": "onwani",
        "scope": REEM,
        "run": "original",
        "original_version": "onwani-reem-v1",
        "original_status": "succeeded",
        "captures": onwani_v1_captures(tmp_path),
    }
    manifest(tmp_path, step, {"real_estate.parcel": 1, "evidence.parcel_observation": 1})
    result = archive.replay_archive(tmp_path, "legacy-replay", str(uuid4()))
    assert result["ok"], (tmp_path / "report.json").read_text()
    run = IngestionRun.objects.get(source__key=collection_for(REEM).parcel_namespace)
    # The run names the reissued request; the observation names the current mapper.
    assert run.connector_version == "onwani-reem-v1"
    observation = ParcelObservation.objects.get()
    assert observation.mapping_version == onwani.VERSION
    # Fields absent from the v1 request stay absent; nothing is filled in.
    assert "ELMS_LANDUSENAME_E" not in observation.raw_attributes
    assert Parcel.objects.get().land_use == "Residential"


def test_unlisted_version_keeps_the_strict_current_request_and_fails(tmp_path):
    step = {
        "operation": "onwani",
        "scope": REEM,
        "run": "original",
        "original_version": "onwani-reem-v0-unrecorded",
        "original_status": "succeeded",
        "captures": onwani_v1_captures(tmp_path),
    }
    manifest(tmp_path, step, {"real_estate.parcel": 1, "evidence.parcel_observation": 1})
    result = archive.replay_archive(tmp_path, "legacy-replay", str(uuid4()))
    assert not result["ok"] and result["failed_steps"] == 1
    assert not Parcel.objects.exists()


def test_named_poi_overpass_receipt_replays_with_its_recorded_query(tmp_path):
    AdministrativeArea.objects.create(
        source_namespace="dmt:onwani:reem:district",
        source_record_id="district",
        name="AL REEM ISLAND",
        kind="district",
        geometry=MultiPolygon(Polygon.from_bbox((54.39, 24.49, 54.42, 24.52)), srid=4326),
    )
    step = {
        "operation": "map",
        "scope": f"{REEM}:osm",
        "run": "original",
        "original_version": "reem-map-v1",
        "original_status": "succeeded",
        "captures": overpass_captures(tmp_path),
    }
    manifest(
        tmp_path,
        step,
        {
            "real_estate.building": 1,
            "real_estate.administrative_area": 1,
            "evidence.map_observation": MapObservation.objects.count() + 1,
        },
    )
    result = archive.replay_archive(tmp_path, "legacy-replay", str(uuid4()))
    assert result["ok"], (tmp_path / "report.json").read_text()
    run = IngestionRun.objects.get(source__key=collection_for(REEM).map_namespace("osm"))
    assert run.connector_version == "reem-map-v1"
    assert Building.objects.count() == 1
    assert MapObservation.objects.get(building__isnull=False).mapping_version == (
        map_sources.VERSION
    )
    # The same bytes cannot answer the current query: no silent substitution.
    step["original_version"] = map_sources.VERSION
    manifest(tmp_path, step, {})
    assert archive.replay_archive(tmp_path, "legacy-replay", str(uuid4()))["failed_steps"] == 1


def test_historical_protocol_is_refused_outside_a_replayed_onwani_or_map_import():
    from property_platform.modules.evidence import orchestration

    historical = legacy.historical_protocol("onwani", REEM, "onwani-reem-v1")
    with pytest.raises(ValueError, match="historical protocol"):
        orchestration.execute_import(
            operation="onwani",
            scope=REEM,
            execution_key="a" * 64,
            actor="legacy-replay",
            historical=historical,
        )
