"""Transport adapters for the API's existing, territory-specific GIS protocols."""

from urllib.parse import urlencode

from property_platform.modules.evidence import map_sources, onwani

from .http import AcquisitionError, SourceHTTP


def _object_ids(value):
    if not isinstance(value, str):
        raise AcquisitionError("Source object IDs must be a comma-separated batch")
    parts = value.split(",")
    if (
        not 1 <= len(parts) <= 100
        or any(
            not part.isascii()
            or not part.isdecimal()
            or len(part) > 19
            or not 0 < int(part) <= 2**63 - 1
            or str(int(part)) != part
            for part in parts
        )
        or len(set(parts)) != len(parts)
    ):
        raise AcquisitionError("Source object IDs must contain 1–100 unique positive integers")


def _arcgis_parameters(params, *, where, fields):
    """Only the three request shapes used by the reviewed domain connector."""
    if not isinstance(params, dict):
        raise AcquisitionError("ArcGIS query parameters must be a mapping")
    if params == {"f": "pjson"}:
        return "metadata"
    if params == {"f": "json", "where": where, "returnIdsOnly": "true"}:
        return "listing"
    if (
        set(params) != {"f", "where", "objectIds", "outFields", "outSR", "returnGeometry"}
        or params["f"] != "json"
        or params["where"] != where
        or params["outFields"] != fields
        or str(params["outSR"]) != "4326"
        or params["returnGeometry"] != "true"
    ):
        raise AcquisitionError("ArcGIS request differs from the registered territory protocol")
    _object_ids(params["objectIds"])
    return "batch"


class MapCollector:
    """District, sectors, streets and OSM acquisition without ORM access."""

    def __init__(self, client: SourceHTTP):
        self.client = client

    @staticmethod
    def allowed_urls() -> tuple[str, ...]:
        urls = [map_sources.OSM_URL, map_sources.OSM_MIRROR]
        for base, *_ in map_sources.LAYERS.values():
            urls.extend((base, base + "/query"))
        return tuple(urls)

    def fetch_url(self, base: str, params: dict) -> tuple[bytes, dict]:
        try:
            if base in (map_sources.OSM_URL, map_sources.OSM_MIRROR):
                if params != {"data": map_sources.OSM_QUERY}:
                    raise AcquisitionError("OSM acquisition must use the registered area query")
            else:
                specification = next(
                    (
                        (url, where, fields)
                        for url, where, _, fields in map_sources.LAYERS.values()
                        if base in (url, url + "/query")
                    ),
                    None,
                )
                if specification is None:
                    raise AcquisitionError("Map endpoint is not registered")
                url, where, fields = specification
                shape = _arcgis_parameters(params, where=where, fields=fields)
                if base != (url if shape == "metadata" else url + "/query"):
                    raise AcquisitionError("Unexpected ArcGIS metadata/query endpoint")
            acquisition = self.client.fetch(
                base + "?" + urlencode(params),
                max_bytes=map_sources.MAX_BYTES,
                allowed_base=base,
                # The fixed Overpass query declares a 45-second execution budget.
                # Keep the existing connector's 60-second allowance for its response.
                read_timeout_seconds=60
                if base in (map_sources.OSM_URL, map_sources.OSM_MIRROR)
                else 30,
            )
            return acquisition.payload, acquisition.capture_receipt()
        except AcquisitionError as exc:
            raise map_sources.SourceError(str(exc)) from exc


class OnwaniCollector:
    """The existing parcel connector keeps schema, batch and geometry validation."""

    def __init__(self, client: SourceHTTP):
        self.client = client

    @staticmethod
    def allowed_urls() -> tuple[str, str]:
        return onwani.BASE_URL, onwani.BASE_URL + "/query"

    def fetch(self, params: dict | None = None) -> tuple[bytes, dict]:
        try:
            if params is None:
                base, query = onwani.BASE_URL, {"f": "pjson"}
            else:
                query = {"f": "json", **params}
                _arcgis_parameters(query, where=onwani.WHERE, fields=onwani.FIELDS)
                base = onwani.BASE_URL + "/query"
            acquisition = self.client.fetch(
                base + "?" + urlencode(query), max_bytes=onwani.MAX_BYTES, allowed_base=base
            )
            return acquisition.payload, acquisition.capture_receipt()
        except AcquisitionError as exc:
            raise onwani.SourceError(str(exc)) from exc
