import copy
import json
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from property_platform.modules.evidence import source_fetch
from property_platform.modules.evidence.maps import onwani


def feature():
    return {
        "attributes": {
            "OBJECTID": 1,
            "DISTRICTENG": "AL REEM ISLAND",
            "MUNICIPALITYENG": "ADM",
            "SectorNumber_PlotID": "RT1_C1",
        },
        "geometry": {"rings": [[[54.4, 24.5], [54.41, 24.5], [54.4, 24.51], [54.4, 24.5]]]},
    }


@pytest.mark.parametrize(
    "change",
    [
        {"DISTRICTENG": "SWEIHAN"},
        {"MUNICIPALITYENG": "AAM"},
        {"OBJECTID": True},
        {"OBJECTID": None},
        {"Construction_Status": "x" * 300},
    ],
)
def test_rejects_wrong_territory_identity_and_schema(change):
    record = feature()
    record["attributes"].update(change)
    with pytest.raises(onwani.SourceError):
        onwani.parse_feature(record)


@pytest.mark.parametrize("point", [[181, 24], [54, 91], [float("nan"), 24], [True, 24]])
def test_rejects_invalid_coordinates(point):
    record = feature()
    record["geometry"]["rings"][0][1] = point
    with pytest.raises(onwani.SourceError):
        onwani.parse_feature(record)


def test_raw_dates_are_preserved_without_inventing_publication_time():
    record = feature()
    record["attributes"]["DataReceivedDate"] = 1788825600000
    record["attributes"]["Permit_LastDate"] = None
    original = copy.deepcopy(record)
    parsed = onwani.parse_feature(record)
    assert parsed["attributes"] == original["attributes"]
    assert "source_published_at" not in parsed["values"]
    assert record == original


@pytest.mark.parametrize("ids", [[], [1, 1], [True], ["1"], [-1], None])
def test_rejects_empty_duplicate_or_malformed_identity_lists(ids):
    with pytest.raises(onwani.SourceError):
        onwani.object_ids({"objectIds": ids})


@pytest.mark.parametrize("data", [{"error": {"code": 400}}, {"exceededTransferLimit": True}, []])
def test_rejects_source_errors_and_truncation(data):
    with pytest.raises(onwani.SourceError):
        onwani.decode(json.dumps(data).encode())


def test_rejects_changed_metadata():
    with pytest.raises(onwani.SourceError):
        onwani.validate_metadata({"name": "OTHER"})


def test_http_error_response_is_returned_for_capture_not_discarded():
    payload = b'{"error":{"code":429}}'
    error = HTTPError(onwani.BASE_URL, 429, "rate limited", {}, BytesIO(payload))
    with patch.object(source_fetch.OPENER, "open", side_effect=error):
        raw, receipt = onwani.fetch()
    assert raw == payload
    assert receipt["http_status"] == 429
    assert receipt["fetched_at"] >= receipt["fetched_started_at"]
