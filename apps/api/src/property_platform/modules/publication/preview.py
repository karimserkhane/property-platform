"""Local research projection, deliberately distinct from an approved public dossier."""

from property_platform.modules.catalog.queries import parcel_features, parcel_identity
from property_platform.modules.evidence.onwani import SOURCE_KEY
from property_platform.modules.evidence.queries import parcel_attributes, parcel_provenance


def features(*, bbox, limit, query):
    from .land_use import VERSION, category

    collection = parcel_features(namespace=SOURCE_KEY, bbox=bbox, limit=limit, query=query)
    for feature in collection["features"]:
        feature["properties"]["category"] = category(feature["properties"]["land_use"])
    collection["classification_version"] = VERSION
    return collection


def detail(parcel_id):
    from datetime import UTC, datetime
    from urllib.parse import urlparse

    from property_platform.modules.catalog.map_queries import parcel_surroundings

    from .land_use import category

    parcel = parcel_identity(namespace=SOURCE_KEY, parcel_id=parcel_id)
    if parcel is None:
        return None
    provenance = parcel_provenance(parcel_id=parcel_id, source_key=SOURCE_KEY)
    if provenance is None:
        return None
    parcel["area_m2"] = round(parcel.pop("area").sq_m, 1)
    parcel["category"] = category(parcel["land_use"])
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
