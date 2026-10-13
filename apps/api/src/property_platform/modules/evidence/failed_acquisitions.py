"""Inert receipt validation for completed GIS responses rejected before materialisation."""

from datetime import datetime
from urllib.parse import parse_qs, urlparse

from django.utils import timezone

from . import map_sources, onwani, osm_bootstrap
from .collection_profiles import collection_for


def source_definition(operation, scope):
    profile = collection_for(scope.split(":", 1)[0])
    if operation == "osm_bootstrap":
        return (
            profile.map_namespace("osm"),
            f"OpenStreetMap — {profile.name} (ODbL)",
            osm_bootstrap.URL,
            osm_bootstrap.VERSION,
        )
    if operation == "onwani":
        return (
            profile.parcel_namespace,
            f"DMT / Onwani PLOT — {profile.name}",
            onwani.BASE_URL,
            onwani.VERSION,
        )
    if operation != "map":
        raise ValueError("Failed raw receipts are only supported for GIS connectors")
    layer = scope.rsplit(":", 1)[1]
    if layer == "osm":
        return (
            profile.map_namespace("osm"),
            f"OpenStreetMap — {profile.name} (ODbL)",
            map_sources.OSM_URL,
            map_sources.VERSION,
        )
    return (
        profile.map_namespace(layer),
        f"DMT / Onwani — {profile.name} {layer}",
        profile.map_layers()[layer][0],
        map_sources.VERSION,
    )


def _request_shape(url, operation, scope):
    profile = collection_for(scope.split(":", 1)[0])
    parts = urlparse(url)
    if parts.scheme != "https" or parts.fragment or len(url) > 4000:
        raise ValueError("Unexpected failed GIS receipt URL")
    base = f"{parts.scheme}://{parts.netloc}{parts.path}"
    query = parse_qs(parts.query, strict_parsing=True)
    if any(len(values) != 1 for values in query.values()):
        raise ValueError("Duplicate GIS request parameters")
    params = {key: values[0] for key, values in query.items()}
    if operation == "osm_bootstrap":
        if base != osm_bootstrap.URL or params not in osm_bootstrap.boxes(scope):
            raise ValueError("Unregistered OSM bootstrap window")
        return
    if operation == "map" and scope.endswith(":osm"):
        if base not in (map_sources.OSM_URL, map_sources.OSM_MIRROR) or params != {
            "data": profile.osm_query
        }:
            raise ValueError("OSM receipt does not match its reviewed source query")
        return
    if operation == "onwani":
        expected, where, fields = onwani.BASE_URL, profile.parcel_where, onwani.FIELDS
    else:
        expected, where, _, fields = profile.map_layers()[scope.rsplit(":", 1)[1]]
    if base == expected and params == {"f": "pjson"}:
        return
    if base != expected + "/query":
        raise ValueError("ArcGIS receipt is outside its registered source endpoint")
    if params == {"f": "json", "where": where, "returnIdsOnly": "true"}:
        return
    if (
        set(params) != {"f", "where", "objectIds", "outFields", "outSR", "returnGeometry"}
        or params["f"] != "json"
        or params["where"] != where
        or params["outFields"] != fields
        or params["outSR"] != "4326"
        or params["returnGeometry"] != "true"
    ):
        raise ValueError("ArcGIS receipt parameters differ from the registered protocol")
    ids = params["objectIds"].split(",")
    if (
        not 1 <= len(ids) <= 100
        or len(set(ids)) != len(ids)
        or any(
            not value.isascii()
            or not value.isdecimal()
            or len(value) > 19
            or not 0 < int(value) <= 2**63 - 1
            or str(int(value)) != value
            for value in ids
        )
    ):
        raise ValueError("ArcGIS receipt has an invalid object ID batch")


def validate_received_acquisitions(operation, scope, rows):
    if rows is None:
        return []
    if not isinstance(rows, (list, tuple)) or len(rows) > 205:
        raise ValueError("Failed acquisition journal exceeds its budget")
    if rows and operation not in {"onwani", "map", "osm_bootstrap"}:
        raise ValueError("Only completed GIS source responses can be retained here")
    output, transferred = [], 0
    maximum = onwani.MAX_BYTES if operation == "onwani" else map_sources.MAX_BYTES
    fields = {
        "url",
        "http_status",
        "fetched_started_at",
        "fetched_at",
        "etag",
        "last_modified_raw",
        "acquisition_method",
        "timestamp_basis",
    }
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"payload", "receipt"}:
            raise ValueError("Unexpected failed source journal fields")
        payload, receipt = row["payload"], row["receipt"]
        if (
            not isinstance(payload, bytes)
            or len(payload) > maximum
            or not isinstance(receipt, dict)
            or set(receipt) != fields
        ):
            raise ValueError("Unexpected failed source payload or receipt size")
        transferred += len(payload)
        if transferred > 64 * 1024 * 1024:
            raise ValueError("Failed source journal exceeds its total byte budget")
        _request_shape(receipt["url"], operation, scope)
        started, fetched = receipt["fetched_started_at"], receipt["fetched_at"]
        if (
            not isinstance(started, datetime)
            or not isinstance(fetched, datetime)
            or not timezone.is_aware(started)
            or not timezone.is_aware(fetched)
            or not started <= fetched <= timezone.now()
            or type(receipt["http_status"]) is not int
            or not 100 <= receipt["http_status"] <= 599
            or not isinstance(receipt["etag"], str)
            or len(receipt["etag"]) > 500
            or not isinstance(receipt["last_modified_raw"], str)
            or len(receipt["last_modified_raw"]) > 160
            or receipt["acquisition_method"] != "scheduled_https_collect"
            or receipt["timestamp_basis"] != "collector_clock"
        ):
            raise ValueError("Invalid failed source receipt status, dates or provenance")
        output.append((payload, receipt))
    return output
