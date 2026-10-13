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
from property_platform.modules.evidence.services import import_onwani  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def test_two_territories_can_share_provider_objectid_without_overwriting():
    reem = feature()
    saadiyat = feature()
    saadiyat["attributes"]["DISTRICTENG"] = "AL SAADIYAT ISLAND"
    for territory, row in [("al-reem-island", reem), ("saadiyat-island", saadiyat)]:
        acquired = iter(responses([row]))
        run = import_onwani(
            actor="test",
            territory=territory,
            acquisition=lambda _, acquired=acquired: next(acquired),
        )
        assert run.summary["created"] == 1
    assert Parcel.objects.count() == 2
    assert Parcel.objects.values("source_namespace").distinct().count() == 2


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

    from property_platform.modules.evidence.models import Capture
    from property_platform.modules.evidence.osm_api_protocol import URL
    from property_platform.modules.evidence.osm_bootstrap import import_bootstrap

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
    from property_platform.modules.evidence.orchestration import reference_registry
    from property_platform.modules.evidence.research_import import import_reference

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
