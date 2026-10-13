"""Acquire outside the database transaction, then replay exact request responses.

The first and final ArcGIS ID listing share a URL, so every request key owns a
queue of captures. A replay never issues a request and never invents fetch times.
"""

from collections import defaultdict, deque

from property_platform.modules.evidence import map_sources, onwani

from .http import AcquisitionError
from .map import MapCollector, OnwaniCollector
from .references import ReferenceCollector

MAX_SNAPSHOT_BYTES = 64 * 1024 * 1024


def _params(params):
    return None if params is None else tuple(sorted(params.items()))


class ReplayFetcher:
    """One-use in-memory receipts; missing, exhausted or unexpected calls fail closed."""

    def __init__(self, *, max_total_bytes: int = MAX_SNAPSHOT_BYTES):
        if type(max_total_bytes) is not int or not 1 <= max_total_bytes <= MAX_SNAPSHOT_BYTES:
            raise AcquisitionError("Invalid total snapshot byte budget")
        self._budget = max_total_bytes
        self._size = 0
        self._requests = defaultdict(deque)

    def _acquire(self, key, collect):
        try:
            payload, receipt = collect()
        except (AcquisitionError, onwani.SourceError) as exc:
            self._requests[key].append(map_sources.SourceError(str(exc)))
            raise
        self._size += len(payload)
        if self._size > self._budget:
            raise AcquisitionError("Acquisition exceeds the total snapshot byte budget")
        self._requests[key].append((payload, dict(receipt)))
        return payload, receipt

    def _take(self, key):
        queue = self._requests.get(key)
        if not queue:
            raise AcquisitionError("Domain importer requested an uncollected or exhausted capture")
        result = queue.popleft()
        if isinstance(result, Exception):
            raise result
        payload, receipt = result
        return payload, dict(receipt)

    def onwani(self, params=None):
        return self._take(("onwani", _params(params)))

    def map(self, base, params):
        return self._take(("map", base, _params(params)))

    def reference(self, url):
        return self._take(("reference", url))

    def assert_consumed(self):
        if any(self._requests.values()):
            raise AcquisitionError("Domain importer did not consume its complete acquisition")


def _decode(payload, receipt, *, protocol):
    if receipt["http_status"] != 200:
        raise onwani.SourceError("Source returned a non-success HTTP status")
    return protocol.decode(payload)


def _batch_ids(data, ids):
    if data.get("spatialReference", {}).get("wkid") != 4326:
        raise onwani.SourceError("Unexpected source CRS")
    features = data.get("features")
    if not isinstance(features, list):
        raise onwani.SourceError("Missing source feature list")
    seen = []
    for feature in features:
        oid = feature.get("attributes", {}).get("OBJECTID")
        if type(oid) is not int or oid not in ids or oid in seen:
            raise onwani.SourceError("Unexpected or duplicate source batch identity")
        seen.append(oid)
    if set(seen) != set(ids):
        raise onwani.SourceError("Incomplete source batch")


def precollect_onwani(
    collector: OnwaniCollector, *, max_total_bytes: int = MAX_SNAPSHOT_BYTES
) -> ReplayFetcher:
    replay = ReplayFetcher(max_total_bytes=max_total_bytes)

    def acquire(params=None):
        payload, receipt = replay._acquire(
            ("onwani", _params(params)), lambda: collector.fetch(params)
        )
        return _decode(payload, receipt, protocol=onwani)

    onwani.validate_metadata(acquire())
    listing_params = {"where": onwani.WHERE, "returnIdsOnly": "true"}
    ids = onwani.object_ids(acquire(listing_params))
    for offset in range(0, len(ids), 100):
        batch_ids = ids[offset : offset + 100]
        batch = acquire(
            {
                "where": onwani.WHERE,
                "objectIds": ",".join(map(str, batch_ids)),
                "outFields": onwani.FIELDS,
                "returnGeometry": "true",
                "outSR": "4326",
            }
        )
        _batch_ids(batch, batch_ids)
    if onwani.object_ids(acquire(listing_params)) != ids:
        raise onwani.SourceError("Territory coverage changed during acquisition")
    return replay


def precollect_map(
    collector: MapCollector, layer: str, *, max_total_bytes: int = MAX_SNAPSHOT_BYTES
) -> ReplayFetcher:
    if layer not in (*map_sources.LAYERS, "osm"):
        raise AcquisitionError("Unknown map acquisition layer")
    replay = ReplayFetcher(max_total_bytes=max_total_bytes)

    def acquire(base, params):
        payload, receipt = replay._acquire(
            ("map", base, _params(params)), lambda: collector.fetch_url(base, params)
        )
        return _decode(payload, receipt, protocol=map_sources), receipt

    if layer == "osm":
        try:
            payload, receipt = replay._acquire(
                ("map", map_sources.OSM_URL, _params({"data": map_sources.OSM_QUERY})),
                lambda: collector.fetch_url(map_sources.OSM_URL, {"data": map_sources.OSM_QUERY}),
            )
            if receipt["http_status"] == 429:
                # Do not bypass a provider's rate limit through a mirror.
                return replay
            _decode(payload, receipt, protocol=map_sources)
        except onwani.SourceError:
            acquire(map_sources.OSM_MIRROR, {"data": map_sources.OSM_QUERY})
        return replay
    url, where, geometry_type, fields = map_sources.LAYERS[layer]
    meta, _ = acquire(url, {"f": "pjson"})
    if meta.get("geometryType") != geometry_type or not set(fields.split(",")).issubset(
        {f["name"] for f in meta.get("fields", [])}
    ):
        raise onwani.SourceError("Map source schema changed")
    listing_params = {"f": "json", "where": where, "returnIdsOnly": "true"}
    listing, _ = acquire(url + "/query", listing_params)
    ids = onwani.object_ids(listing)
    for offset in range(0, len(ids), 100):
        batch_ids = ids[offset : offset + 100]
        batch, _ = acquire(
            url + "/query",
            {
                "f": "json",
                "where": where,
                "objectIds": ",".join(map(str, batch_ids)),
                "outFields": fields,
                "outSR": 4326,
                "returnGeometry": "true",
            },
        )
        _batch_ids(batch, batch_ids)
    latest, _ = acquire(url + "/query", listing_params)
    if onwani.object_ids(latest) != ids:
        raise onwani.SourceError("Map coverage changed during acquisition")
    return replay


def precollect_reference(collector: ReferenceCollector, url: str) -> ReplayFetcher:
    replay = ReplayFetcher(max_total_bytes=4 * 1024 * 1024)
    replay._acquire(("reference", url), lambda: collector.fetch_url(url))
    return replay
