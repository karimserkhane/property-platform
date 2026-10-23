"""Local research projection, deliberately distinct from an approved public dossier."""

from property_platform.modules.catalog.queries import parcel_features, parcel_identity
from property_platform.modules.evidence.catalogue_history import recover_display
from property_platform.modules.evidence.queries import (
    parcel_attributes,
    parcel_provenance,
    parcel_sources,
)


def parcel_index(*, bbox, limit, query, namespaces=None, after=None):
    """`features` without footprints, for maps drawing them from parcel tiles."""
    from property_platform.modules.catalog.map_queries import project_markers_near_parcels

    collection = features(
        bbox=bbox, limit=limit, query=query, namespaces=namespaces, after=after, geometry=False
    )
    # Only residential and mixed parcels can receive a potential project name.
    candidates = [
        feature["id"]
        for feature in collection["features"]
        if feature["properties"]["category"] in {"mixed", "residential"}
    ]
    nearby = project_markers_near_parcels(candidates)
    for feature in collection["features"]:
        feature["properties"]["nearby_projects"] = nearby.get(feature["id"], [])
    return collection


def features(*, bbox, limit, query, namespaces=None, after=None, geometry=True):
    from .land_use import VERSION, category
    from .uses import use_types

    collection = parcel_features(
        namespaces=namespaces, bbox=bbox, limit=limit, query=query, after=after, geometry=geometry
    )
    sources = parcel_sources([feature["id"] for feature in collection["features"]])
    recover_display("parcel", [feature["properties"] for feature in collection["features"]])
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

    from property_platform.modules.catalog.map_queries import (
        overlapping_parcels,
        parcel_surroundings,
    )

    from .land_use import category
    from .uses import use_types

    parcel = parcel_identity(namespaces=namespaces, parcel_id=parcel_id)
    if parcel is None:
        return None
    recover_display("parcel", [parcel])
    parcel_id = parcel["id"]
    provenance = parcel_provenance(parcel_id=parcel_id, source_key=parcel.pop("source_namespace"))
    if provenance is None:
        return None
    parcel["area_m2"] = round(parcel.pop("area").sq_m, 1)
    parcel["category"] = category(parcel["land_use"])
    parcel["use_types"] = use_types(land_use=parcel["land_use"])
    attrs = parcel_attributes(parcel_id, with_history=True)
    parcel["field_history"].update(attrs.pop("_field_history"))

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
    overlaps = []
    for row in overlapping_parcels(parcel_id, namespaces=namespaces):
        source = parcel_provenance(parcel_id=row["id"], source_key=row.pop("source_namespace"))
        if source is None:
            continue
        other = parcel_attributes(row["id"])
        overlaps.append(
            {
                **row,
                "use_types": use_types(land_use=row["land_use"]),
                "ownership": other.get("OWNERSHIPTYPE") or "",
                "source": source,
            }
        )
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
        "overlapping_parcels": overlaps,
        "source": provenance,
        "publication_status": "local_preview",
    }
