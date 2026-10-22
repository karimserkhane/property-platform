"""AD-SDI snapshot completeness and capture replay without network or database."""

import httpx
import pytest
from property_platform.modules.evidence import sdi_protocol as protocol
from test_collectors import client

from property_platform_ingestion.collectors.sdi import precollect_sdi


def handler_for(*, changed=False, incomplete=False, commercial=2):
    calls = []

    def handler(request):
        params = request.url.params
        calls.append(dict(params))
        if request.url.path.endswith("/10"):
            data = {
                "name": "Plots",
                "geometryType": "esriGeometryPolygon",
                "extent": {"spatialReference": {"wkid": 4326}},
                "typeIdField": "PRIMARYUSEENG",
                "fields": [{"name": name} for name in protocol.FIELDS.split(",")],
                "types": [
                    {"id": commercial, "name": "Commercial"},
                    {"id": 13, "name": "Residential"},
                ],
            }
        elif params.get("returnIdsOnly") == "true":
            data = {"objectIds": [1, 2] if changed and len(calls) == 4 else [1]}
        else:
            data = {
                "spatialReference": {"wkid": 4326},
                "features": [] if incomplete else [{"attributes": {"OBJECTID": 1}}],
            }
        return httpx.Response(200, json=data)

    return calls, handler


def test_sdi_replays_both_listings_and_preserves_exact_capture_receipts():
    calls, handler = handler_for()
    with client([protocol.URL, protocol.URL + "/query"], handler) as http:
        replay = precollect_sdi(http, "al-maryah-island")
    assert len(calls) == 4
    assert calls[1] == calls[3]
    assert calls[2]["outFields"] == protocol.FIELDS
    assert calls[2]["where"] == protocol.where("al-maryah-island")
    for params in calls:
        base = protocol.URL if params == {"f": "pjson"} else protocol.URL + "/query"
        payload, receipt = replay.map(base, params)
        assert protocol.decode(payload)
        assert receipt["fetched_at"] >= receipt["fetched_started_at"]
        assert receipt["http_status"] == 200
    replay.assert_consumed()


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"changed": True}, "changed during acquisition"),
        ({"incomplete": True}, "Incomplete source batch"),
        ({"commercial": 20}, "subtype dictionary changed"),
    ],
)
def test_sdi_refuses_changing_incomplete_or_reclassified_snapshots(options, message):
    _, handler = handler_for(**options)
    with client([protocol.URL, protocol.URL + "/query"], handler) as http:
        with pytest.raises(protocol.SourceError, match=message):
            precollect_sdi(http, "al-maryah-island")
