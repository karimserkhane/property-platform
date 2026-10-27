import json
import os
from datetime import UTC, datetime

import pytest

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("AD-SDI integration requires real PostGIS", allow_module_level=True)

from test_onwani_postgis import feature, run  # noqa: E402

from property_platform.modules.catalog.models import Parcel  # noqa: E402
from property_platform.modules.evidence.maps import sdi_protocol as protocol  # noqa: E402
from property_platform.modules.evidence.maps.sdi_import import import_parcels  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    IngestionRun,
    ParcelObservation,
    QuarantinedObservation,
)
from property_platform.modules.publication.land_use import category  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def test_sdi_primary_uses_do_not_borrow_numeric_codes_or_specific_amenities():
    for value in ("Educational", "Religious", "Health", "Recreational", "Public"):
        assert category(value) == "public"
    assert category("Commercial") == "mixed"
    assert category("Residential") == "residential"
    assert category("Utility") == "tech"
    assert category("Undefined") == "unknown"


def sdi_feature(plot="91", territory="al-maryah-island"):
    row = feature()
    row["attributes"] = {
        "OBJECTID": 1,
        "PLOTID": plot,
        "PLOTNUMBER": "C1",
        "COMMUNITYENG": "MI5",
        "DISTRICTENG": protocol.collection_for(territory).district_name,
        "MUNICIPALITYENG": "ADM",
        "PRIMARYUSEENG": 13,
        "PRIMARYUSEARA": "",
        "SOURCEOFORIGIN": "ABU DHABI MUNICIPALITY",
    }
    return row


def acquire_for(row, *, incomplete=False):
    ids = {"objectIds": [1]}
    meta = {
        "name": "Plots",
        "geometryType": "esriGeometryPolygon",
        "extent": {"spatialReference": {"wkid": 4326}},
        "typeIdField": "PRIMARYUSEENG",
        "fields": [{"name": f} for f in protocol.FIELDS.split(",")],
        "types": [{"id": 2, "name": "Commercial"}, {"id": 13, "name": "Residential"}],
    }
    responses = iter(
        [
            meta,
            ids,
            {"features": [] if incomplete else [row], "spatialReference": {"wkid": 4326}},
            ids,
        ]
    )

    def acquire(base, params):
        now = datetime.now(UTC)
        return json.dumps(next(responses)).encode(), {
            "url": base,
            "http_status": 200,
            "fetched_started_at": now,
            "fetched_at": now,
            "etag": "",
            "last_modified_raw": "",
        }

    return acquire


def test_new_maryah_parcels_replay_without_duplicates_and_keep_exact_history():
    for index in range(2):
        result = import_parcels(
            territory="al-maryah-island", actor="test", acquisition=acquire_for(sdi_feature())
        )
        assert result.summary["created" if index == 0 else "unchanged"] == 1
    parcel = Parcel.objects.get()
    assert parcel.official_plot_id == "91" and parcel.geometry.valid
    assert parcel.land_use == "Residential"
    assert ParcelObservation.objects.filter(parcel=parcel).count() == 2
    assert Capture.objects.count() == 8
    assert all(
        o.ingested_at and o.capture.fetched_at
        for o in ParcelObservation.objects.select_related("capture")
    )


def test_same_official_id_compares_without_overwriting_richer_onwani_fields():
    original = feature()
    original["attributes"].update(PLOTID="91", ELMS_LANDUSENAME_E="Residential Apartments")
    run([original])
    before = Parcel.objects.get()
    result = import_parcels(
        territory="al-reem-island",
        actor="test",
        acquisition=acquire_for(sdi_feature(territory="al-reem-island")),
    )
    before.refresh_from_db()
    assert Parcel.objects.count() == 1
    assert before.land_use == "Residential Apartments" and before.revision == 1
    assert result.summary["compared"] == result.summary["consistent"] == 1


def test_same_id_different_geometry_is_quarantined_without_moving_the_parcel():
    original = feature()
    original["attributes"]["PLOTID"] = "91"
    run([original])
    before = Parcel.objects.get().geometry.wkt
    row = sdi_feature(territory="al-reem-island")
    for ring in row["geometry"]["rings"]:
        for point in ring:
            point[0] += 0.02
    result = import_parcels(territory="al-reem-island", actor="test", acquisition=acquire_for(row))
    assert result.summary["geometry_conflict"] == 1 and result.status == "quarantined"
    assert Parcel.objects.get().geometry.wkt == before
    assert QuarantinedObservation.objects.count() == 1


def test_same_geometry_different_ids_does_not_create_a_duplicate():
    original = feature()
    original["attributes"]["PLOTID"] = "old-91"
    run([original])
    result = import_parcels(
        territory="al-reem-island",
        actor="test",
        acquisition=acquire_for(sdi_feature(territory="al-reem-island")),
    )
    assert result.status == "quarantined" and Parcel.objects.count() == 1


def test_incomplete_snapshot_never_materializes_partial_parcels():
    with pytest.raises(protocol.SourceError):
        import_parcels(
            territory="al-maryah-island",
            actor="test",
            acquisition=acquire_for(sdi_feature(), incomplete=True),
        )
    assert not Parcel.objects.exists()
    assert IngestionRun.objects.get().status == "failed" and Capture.objects.count() == 3


def test_emirate_district_scope_keeps_its_own_municipality_and_source():
    row = sdi_feature()
    row["attributes"].update(DISTRICTENG="AL BATEEN", MUNICIPALITYENG="AAM", COMMUNITYENG="")
    run = import_parcels(territory="aam:al-bateen", actor="test", acquisition=acquire_for(row))
    assert run.summary["created"] == 1
    parcel = Parcel.objects.get()
    assert (parcel.municipality, parcel.district) == ("AAM", "AL BATEEN")
    assert parcel.source_namespace == "ad-sdi:generic-search:plots:aam:al-bateen"


def test_same_district_name_in_another_municipality_never_enters_the_scope():
    row = sdi_feature()
    row["attributes"].update(DISTRICTENG="AL BATEEN", MUNICIPALITYENG="ADM")
    with pytest.raises(protocol.SourceError, match="outside requested municipality"):
        import_parcels(territory="aam:al-bateen", actor="test", acquisition=acquire_for(row))
    assert not Parcel.objects.exists()
