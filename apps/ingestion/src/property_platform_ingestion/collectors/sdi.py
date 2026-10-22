"""Bounded, allowlisted AD-SDI acquisition before entering the domain transaction."""

from urllib.parse import urlencode

from property_platform.modules.evidence import sdi_protocol as protocol

from .map import _arcgis_parameters
from .snapshots import ReplayFetcher, _batch_ids, _params


def precollect_sdi(client, territory):
    replay = ReplayFetcher()

    def acquire(base, params):
        shape = _arcgis_parameters(params, where=protocol.where(territory), fields=protocol.FIELDS)
        if base != (protocol.URL if shape == "metadata" else protocol.URL + "/query"):
            raise ValueError("AD-SDI endpoint outside reviewed scope")

        def collect():
            item = client.fetch(
                base + "?" + urlencode(params), allowed_base=base, max_bytes=protocol.MAX_BYTES
            )
            return item.payload, item.capture_receipt()

        payload, receipt = replay._acquire(("map", base, _params(params)), collect)
        if receipt["http_status"] != 200:
            raise protocol.SourceError("AD-SDI HTTP failure")
        return protocol.decode(payload)

    protocol.metadata(acquire(protocol.URL, {"f": "pjson"}))
    listing = {"f": "json", "where": protocol.where(territory), "returnIdsOnly": "true"}
    ids = protocol.object_ids(acquire(protocol.URL + "/query", listing))
    for offset in range(0, len(ids), 100):
        subset = ids[offset : offset + 100]
        data = acquire(
            protocol.URL + "/query",
            {
                "f": "json",
                "where": protocol.where(territory),
                "objectIds": ",".join(map(str, subset)),
                "outFields": protocol.FIELDS,
                "returnGeometry": "true",
                "outSR": "4326",
            },
        )
        _batch_ids(data, subset)
    if protocol.object_ids(acquire(protocol.URL + "/query", listing)) != ids:
        raise protocol.SourceError("AD-SDI territory changed during acquisition")
    return replay
