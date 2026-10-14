"""Local research projection, deliberately distinct from an approved public dossier."""

from property_platform.modules.catalog.queries import parcel_features, parcel_identity
from property_platform.modules.evidence.queries import (
    parcel_attributes,
    parcel_provenance,
    parcel_sources,
)


def features(*, bbox, limit, query, namespaces=None, after=None):
    from .land_use import VERSION, category
    from .uses import use_types

    collection = parcel_features(
        namespaces=namespaces, bbox=bbox, limit=limit, query=query, after=after
    )
    sources = parcel_sources([feature["id"] for feature in collection["features"]])
    for feature in collection["features"]:
        feature["properties"]["category"] = category(feature["properties"]["land_use"])
        feature["properties"]["use_types"] = use_types(land_use=feature["properties"]["land_use"])
        source = sources.get(feature["id"], {})
        feature["properties"]["source_url"] = source.get("url")
        feature["properties"]["source_name"] = source.get("name")
    collection["classification_version"] = VERSION
    return collection


def detail(parcel_id, namespaces=None):
    from datetime import UTC, datetime
    from urllib.parse import urlparse

    from property_platform.modules.catalog.map_queries import parcel_surroundings

    from .land_use import category
    from .uses import use_types

    parcel = parcel_identity(namespaces=namespaces, parcel_id=parcel_id)
    if parcel is None:
        return None
    parcel_id = parcel["id"]
    provenance = parcel_provenance(parcel_id=parcel_id, source_key=parcel.pop("source_namespace"))
    if provenance is None:
        return None
    parcel["area_m2"] = round(parcel.pop("area").sq_m, 1)
    parcel["category"] = category(parcel["land_use"])
    parcel["use_types"] = use_types(land_use=parcel["land_use"])
    attrs = parcel_attributes(parcel_id)

    def day(key):
        value = attrs.get(key)
        if type(value) not in (int, float):
            return None
        try:
            return datetime.fromtimestamp(value / 1000, UTC).date().isoformat()
        except ValueError, OverflowError, OSError:
            return None

    url = attrs.get("DMT_DCR_URL") or ""
    places, streets = parcel_surroundings(parcel_id)
    for row in streets:
        row["distance_m"] = round(row.pop("distance").m, 1)
    parcel["attributes"] = {
        "planning": attrs.get("PLANNINGSTATUS") or "",
        "ownership": attrs.get("OWNERSHIPTYPE") or "",
        "allocation": attrs.get("ELMS_AllocationStatus") or "",
        "approval_date": day("APPROVALDATE"),
        "received_date": day("DataReceivedDate"),
        "permit_date": day("Permit_LastDate"),
        "permit_type": attrs.get("Permit_LastType") or "",
        "meps": attrs.get("MEPS_CONS_STATUS") or "",
        "meps_updated": attrs.get("MEPS_CONS_UPDATEON") or "",
        "dcr_url": url if urlparse(url).scheme == "https" else "",
    }
    return {
        **parcel,
        "places": places,
        "streets": streets,
        "source": provenance,
        "publication_status": "local_preview",
    }
