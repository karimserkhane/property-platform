import os

import pytest

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Saadiyat integration requires real PostGIS", allow_module_level=True)

from django.contrib.gis.geos import MultiPolygon, Polygon  # noqa: E402
from test_onwani_postgis import feature, responses  # noqa: E402
from test_osm_api_protocol import XML  # noqa: E402

from property_platform.modules.catalog.models import AdministrativeArea, Building, Parcel  # noqa: E402
from property_platform.modules.catalog.queries import parcel_features  # noqa: E402
from property_platform.modules.evidence.collection_profiles import collection_for  # noqa: E402
from property_platform.modules.evidence.maps.services import import_onwani  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def test_whole_area_reads_both_islands_without_leaking_other_sources(client):
    import json

    from django.test import override_settings
    from test_reem_map_postgis import osm, receipt

    from property_platform.modules.evidence.maps.map_import import import_map_layer
    from property_platform.modules.publication.coverage import coverage_registry

    bounds = (54.4, 24.5, 54.42, 24.52)
    identities = []
    for member in ("al-reem-island", "saadiyat-island"):
        profile = collection_for(member)
        row = feature()
        row["attributes"]["DISTRICTENG"] = profile.district_name
        row["geometry"]["rings"] = list(Polygon.from_bbox(bounds).coords)
        acquired = iter(responses([row]))
        import_onwani(
            actor="test", territory=member, acquisition=lambda _, acquired=acquired: next(acquired)
        )
        parcel = Parcel.objects.get(source_namespace=profile.parcel_namespace)
        identities.append(str(parcel.id))
        AdministrativeArea.objects.create(
            source_namespace=profile.map_namespace("district"),
            source_record_id="1",
            name=profile.district_name,
            kind="district",
            geometry=MultiPolygon(Polygon.from_bbox(bounds), srid=4326),
        )
        data = osm()
        data["elements"][0]["tags"]["name"] = member
        import_map_layer(
            layer="osm",
            actor="test",
            territory=member,
            replay=(json.dumps(data).encode(), receipt()),
        )
    Parcel.objects.create(
        source_namespace="future-unreviewed-source",
        source_record_id="1",
        code="outside",
        geometry=MultiPolygon(Polygon.from_bbox(bounds), srid=4326),
    )
    Building.objects.create(
        source_namespace="future-unreviewed-source",
        source_record_id="way/1",
        name="outside",
        geometry=MultiPolygon(Polygon.from_bbox(bounds), srid=4326),
    )
    registry = coverage_registry()
    scope = next(row for row in registry["territories"] if row["id"] == "abu-dhabi")
    assert scope["parcel_count"] == 2
    assert scope["queryable"]
    assert scope["collection_bounds"] == (54.383, 24.465, 54.483, 24.603)
    query = {"bbox": "54.39,24.49,54.43,24.53", "territory": "abu-dhabi"}
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        parcels = client.get("/api/v1/preview/parcels", {**query, "limit": 1})
        assert parcels.status_code == 200
        first = parcels.json()
        second = client.get(
            "/api/v1/preview/parcels",
            {
                **query,
                "limit": 1,
                "after": first["next_cursor"],
            },
        )
        assert second.status_code == 200
        assert {row["id"] for row in first["features"] + second.json()["features"]} == set(
            identities
        )
        assert not second.json()["truncated"]
        context = client.get("/api/v1/preview/map-context", query)
        assert context.status_code == 200
        assert {row["properties"]["name"] for row in context.json()["building"]["features"]} == {
            "al-reem-island",
            "saadiyat-island",
        }
        assert all(
            set(row["properties"]["parcel_ids"]) == set(identities)
            for row in context.json()["place"]["features"]
        )
        for parcel_id in identities:
            assert (
                client.get(
                    f"/api/v1/preview/parcels/{parcel_id}", {"territory": "abu-dhabi"}
                ).status_code
                == 200
            )


def test_three_territories_can_share_provider_objectid_without_overwriting():
    for territory in ("al-reem-island", "saadiyat-island", "al-maryah-island"):
        row = feature()
        row["attributes"]["DISTRICTENG"] = collection_for(territory).district_name
        acquired = iter(responses([row]))
        run = import_onwani(
            actor="test",
            territory=territory,
            acquisition=lambda _, acquired=acquired: next(acquired),
        )
        assert run.summary["created"] == 1
    assert Parcel.objects.count() == 3
    assert Parcel.objects.values("source_namespace").distinct().count() == 3


def test_cursor_pages_are_complete_stable_and_isolated():
    profile = collection_for("saadiyat-island")
    for territory in ("al-reem-island", "saadiyat-island"):
        for i in range(5):
            Parcel.objects.create(
                source_namespace=collection_for(territory).parcel_namespace,
                source_record_id=str(i),
                code=f"P{i}",
                geometry=MultiPolygon(Polygon.from_bbox((54.41, 24.54, 54.42, 24.55)), srid=4326),
            )
    ids, after = [], None
    while True:
        page = parcel_features(
            bbox=(54.4, 24.53, 54.43, 24.56),
            limit=2,
            namespaces=(profile.parcel_namespace,),
            after=after,
        )
        ids.extend(row["id"] for row in page["features"])
        after = page["next_cursor"]
        if not after:
            break
    assert len(ids) == len(set(ids)) == 5
    assert ids == sorted(ids)


def test_bootstrap_retains_raw_windows_and_deduplicates_shared_objects():
    from datetime import UTC, datetime

    from property_platform.modules.evidence.maps.osm_api_protocol import URL
    from property_platform.modules.evidence.maps.osm_bootstrap import import_bootstrap
    from property_platform.modules.evidence.models import Capture

    profile = collection_for("saadiyat-island")
    AdministrativeArea.objects.create(
        source_namespace=profile.map_namespace("district"),
        source_record_id="92",
        name=profile.district_name,
        kind="district",
        geometry=MultiPolygon(Polygon.from_bbox((54.4, 24.53, 54.43, 24.56)), srid=4326),
    )
    now = datetime.now(UTC)

    def acquisition(url, params):
        return XML, {
            "url": URL,
            "http_status": 200,
            "fetched_started_at": now,
            "fetched_at": now,
            "etag": "",
            "last_modified_raw": "",
        }

    run = import_bootstrap(territory="saadiyat-island", actor="test", acquisition=acquisition)
    assert run.summary["created"] == 2
    assert Building.objects.count() == 1
    assert Capture.objects.filter(run=run).count() == 4
    assert all(bytes(row.payload) == XML for row in Capture.objects.filter(run=run))
    assert Building.objects.get().source_namespace == profile.map_namespace("osm")


def test_overlapping_windows_do_not_link_places_to_the_other_territory():
    from django.contrib.gis.geos import Point

    from property_platform.modules.catalog.map_queries import map_rows
    from property_platform.modules.catalog.models import Place

    profiles = [collection_for(t) for t in ("al-reem-island", "saadiyat-island")]
    parcels = []
    for profile in profiles:
        parcels.append(
            Parcel.objects.create(
                source_namespace=profile.parcel_namespace,
                source_record_id="1",
                code="1",
                geometry=MultiPolygon(Polygon.from_bbox((54.41, 24.54, 54.42, 24.55)), srid=4326),
            )
        )
        Place.objects.create(
            source_namespace=profile.map_namespace("osm"),
            source_record_id="node/1",
            name=profile.name,
            geometry=Point(54.415, 24.545, srid=4326),
        )
    rows, truncated = map_rows(
        "place",
        (54.4, 24.53, 54.43, 24.56),
        namespaces=(profiles[1].map_namespace("osm"),),
        parcel_namespaces=(profiles[1].parcel_namespace,),
    )
    assert not truncated and len(rows) == 1
    assert rows[0]["name"] == "Saadiyat Island"
    assert rows[0]["parcel_ids"] == [parcels[1].id]


def test_reference_reprocessing_is_scoped_to_its_registry():
    from datetime import UTC, datetime
    from io import StringIO

    from django.core.management import call_command

    from property_platform.modules.evidence.models import ResearchReference
    from property_platform.modules.evidence.rebuild.orchestration import reference_registry
    from property_platform.modules.evidence.sources.research_import import import_reference

    now = datetime.now(UTC)
    for territory in ("al-reem-island", "saadiyat-island"):
        row = reference_registry(territory)[0]

        def acquisition(url):
            return b"<title>Test</title>", {
                "url": url,
                "http_status": 200,
                "fetched_started_at": now,
                "fetched_at": now,
                "etag": "",
                "last_modified_raw": "",
            }

        import_reference(row, actor="test", acquisition=acquisition, territory=territory)
    call_command(
        "import_reem_references",
        actor="test",
        territory="saadiyat-island",
        reprocess=True,
        stdout=StringIO(),
    )
    copied = ResearchReference.objects.filter(capture__parent_capture__isnull=False)
    assert copied.count() == 1
    assert copied.get().capture.run.source.url == reference_registry("saadiyat-island")[0]["url"]
