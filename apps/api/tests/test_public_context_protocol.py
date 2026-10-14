import base64
import hashlib
import json
from datetime import UTC, datetime

import pytest

from property_platform.modules.evidence import abu_dhabi, adrec


def facility(identity=61, **changes):
    return {
        "FacilityID": identity,
        "FacilityName": "Example Hospital",
        "FacilityType": "Hospital",
        "Address": None,
        "IsPlannedProperty": False,
        "Latitude": 24.5,
        "Longitude": 54.4,
        **changes,
    }


def school(**changes):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [54.4, 24.5]},
        "properties": {
            "SCH_EDUCATION_TYPE_DESC": "Charter",
            "SCH_ESIS_ID": "6001",
            "SCH_NAME_EN": "Example School",
            "SCH_NAME_AR": "مدرسة",
            "SCH_MUNICIPALITY_EN": "ABU DHABI",
            **changes,
        },
    }


def district(identity=1):
    return {
        "type": "Feature",
        "id": identity,
        "properties": {
            "OBJECTID": identity,
            "DISTRICTID": identity,
            "NAMEENGLISH": "District",
            "NAMEARABIC": "منطقة",
            "MUNICIPALITYNAME": "ADM",
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[54.4, 24.5], [54.41, 24.5], [54.41, 24.51], [54.4, 24.5]]],
        },
    }


def test_district_geometry_and_identity_lists_prove_complete_coverage():
    body = json.dumps({"type": "FeatureCollection", "features": [district()]}).encode()
    identities = json.dumps({"objectIds": [1]}).encode()
    calls = []

    def acquire(url, params):
        calls.append(url)
        return (identities if url == abu_dhabi.DISTRICT_IDS else body), "proof"

    proof, rows, _ = abu_dhabi.collect("abu-dhabi:districts", acquire)
    assert proof == "proof" and rows[0][2]["municipality"] == "ADM"
    assert calls == [abu_dhabi.DISTRICT_IDS, abu_dhabi.DISTRICT_GEOJSON, abu_dhabi.DISTRICT_IDS]
    with pytest.raises(abu_dhabi.ContextError):
        abu_dhabi.collect(
            "abu-dhabi:districts",
            lambda u, p: (
                json.dumps({"objectIds": [1, 2]}).encode() if u == abu_dhabi.DISTRICT_IDS else body,
                "proof",
            ),
        )


def test_context_preserves_planned_status_arabic_and_original_paths():
    rows, modified = abu_dhabi.parse(
        "abu-dhabi:health", json.dumps([facility(IsPlannedProperty=True)]).encode()
    )
    assert rows[0][2]["planned"] is True and rows[0][2]["address"] == ""
    assert rows[0][0] == "[0]" and modified is None
    rows, _ = abu_dhabi.parse(
        "abu-dhabi:schools",
        json.dumps({"type": "FeatureCollection", "features": [school()]}).encode(),
    )
    assert rows[0][2]["name_ar"] == "مدرسة" and rows[0][0] == "features[0]"


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [facility(), facility()],
        [facility(FacilityID=True)],
        [facility(Latitude=None)],
        [facility(Longitude=0)],
        [facility(IsPlannedProperty=None)],
        [facility(FacilityName="")],
        [facility(Latitude=float("nan"))],
    ],
)
def test_empty_duplicate_unknown_status_bad_id_and_geometry_reject_the_batch(rows):
    with pytest.raises(abu_dhabi.ContextError):
        abu_dhabi.parse("abu-dhabi:health", json.dumps(rows).encode())


def test_non_charter_school_and_non_geojson_fail():
    for payload in [
        b"{}",
        json.dumps(
            {"type": "FeatureCollection", "features": [school(SCH_EDUCATION_TYPE_DESC="Private")]}
        ).encode(),
    ]:
        with pytest.raises(abu_dhabi.ContextError):
            abu_dhabi.parse("abu-dhabi:schools", payload)


def test_bus_select_is_inert_and_scoped_not_every_option_on_the_page():
    html = (
        b'<select><option value="junk">Ignored</option></select>'
        b'<select id="drpBusRoutes"><option value="auh:11005:P:H:6p2" '
        b'data-busnum="5" data-from="A" data-to="B">City Bus 5</option></select>'
        b"<script>throw new Error()</script>"
    )
    rows, _ = abu_dhabi.parse("abu-dhabi:mobility", html)
    assert len(rows) == 1 and rows[0][2]["origin"] == "A"
    with pytest.raises(abu_dhabi.ContextError):
        abu_dhabi.parse("abu-dhabi:mobility", html + html)


def test_census_reference_year_modified_day_and_rounding_are_distinct():
    dataset = {
        "@graph": [
            {
                "@type": "Dataset",
                "spatialCoverage": {"name": "Emirate of Abu Dhabi, United Arab Emirates"},
                "description": "All statistics are rounded to a multiple of 5.",
                "temporalCoverage": "2024",
                "dateModified": "2025-07-01",
                "variableMeasured": [
                    {
                        "name": "Buildings, Al Ain Region, 2024",
                        "unitText": "buildings",
                        "value": 114715,
                    }
                ],
            }
        ]
    }
    html = ('<script type="application/ld+json">' + json.dumps(dataset) + "</script>").encode()
    rows, modified = abu_dhabi.parse("abu-dhabi:statistics", html)
    assert rows[0][2]["region"] == "Al Ain Region"
    assert rows[0][2]["reference_year"] == 2024 and rows[0][2]["rounding_base"] == 5
    assert str(modified) == "2025-07-01"
    with pytest.raises(abu_dhabi.ContextError):
        abu_dhabi.parse("abu-dhabi:statistics", html.replace(b"multiple of 5", b"multiple of 10"))
    with pytest.raises(abu_dhabi.ContextError):
        abu_dhabi.parse("abu-dhabi:statistics", html + html)


def test_urls_and_scope_are_not_visitor_configurable():
    with pytest.raises(abu_dhabi.ContextError):
        abu_dhabi.feed_for("dubai:health")
    with pytest.raises(abu_dhabi.ContextError):
        abu_dhabi.validate_request("abu-dhabi:health", "https://example.com", {})
    with pytest.raises(abu_dhabi.ContextError):
        abu_dhabi.validate_request("abu-dhabi:health", abu_dhabi.FEEDS["health"].url, {"limit": 1})


def test_emirate_adrec_uses_all_districts_without_changing_island_filters():
    scope = adrec.sales_scope("abu-dhabi")
    assert adrec.sales_params(scope)["district"] == "all"
    assert (
        adrec.sales_params(adrec.sales_scope("saadiyat-island"))["district"] == "Al Saadiyat Island"
    )


def school_archive():
    body = json.dumps({"type": "FeatureCollection", "features": [school()]}).encode()
    return {
        "scope": "abu-dhabi:schools",
        "url": abu_dhabi.FEEDS["schools"].url,
        "payload_base64": base64.b64encode(body).decode(),
        "sha256": hashlib.sha256(body).hexdigest(),
        "http_status": 200,
        "fetched_at": datetime.now(UTC).isoformat(),
        "timestamp_basis": "artifact_filesystem_time",
        "acquisition_method": "manual_archive_import",
    }


def test_archive_preserves_approximate_time_and_rejects_tampering_or_fake_freshness():
    row = school_archive()
    body, receipt = abu_dhabi.archive_response("abu-dhabi:schools", row)
    assert receipt["fetched_started_at"] is None
    assert receipt["timestamp_basis"] == "artifact_filesystem_time"
    assert abu_dhabi.parse("abu-dhabi:schools", body)[0][0][2]["source_record_id"] == "6001"
    for changes in [
        {"sha256": "0" * 64},
        {"url": "https://example.com"},
        {"timestamp_basis": "collector_clock"},
        {"fetched_at": "2099-01-01T00:00:00+00:00"},
    ]:
        with pytest.raises(abu_dhabi.ContextError):
            abu_dhabi.archive_response("abu-dhabi:schools", {**row, **changes})
