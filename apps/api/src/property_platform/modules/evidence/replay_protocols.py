"""Historical acquisition protocols that a capture replay may reissue exactly.

A rebuild replays archived bytes through the current typed importers. When the
original requests differ from the current ones (other Onwani `outFields`, another
Overpass query), the importer must reissue the historical request, record that
protocol on its run and keep the current mapping version on its observations. A
replay never answers a current request with the bytes of another request, and an
unlisted version keeps the current protocol, so the strict URL check still fails.

Entries are copied from the connector sources at the cited commits, never inferred
from a receipt.
"""

from dataclasses import dataclass

from .collection_profiles import collection_for


@dataclass(frozen=True)
class AcquisitionProtocol:
    version: str
    onwani_fields: str | None = None
    osm_query: str | None = None


# `onwani.py` at fcd4598 (11 Oct 2026): seven land-use/planning fields were added in
# onwani-reem-v2 (087241d). Later versions request the current field list.
ONWANI_FIELDS = {
    "onwani-reem-v1": (
        "OBJECTID,PLOTID,GISID,SectorNumber_PlotID,DISTRICTENG,DISTRICTID,"
        "MUNICIPALITYENG,COMMUNITYENG,ELMS_LandUse_Const,Construction_Status,"
        "APPROVALDATE,MODIFIEDDATE,DataReceivedDate,Permit_LastDate,Permit_LastType,"
        "MEPS_CONS_STATUS,MEPS_CONS_UPDATEON,DMT_DCR_URL"
    ),
}

# `map_sources.py` at 087241d and `collection_profiles.py` at 001b65c: only named
# amenities/leisure, no shop or transport selectors, until district-map-v5 (06af8b2).
# reem-map-v1 predates the first commit; its archived receipts carry the same query.
NAMED_POI_OSM_VERSIONS = frozenset({"reem-map-v1", "reem-map-v2", "reem-map-v3", "district-map-v4"})


def named_poi_osm_query(territory):
    west, south, east, north = collection_for(territory).osm_bounds
    bbox = f"({south},{west},{north},{east})"
    return (
        "[out:json][timeout:45];("
        f"way[building]{bbox};way[highway][name]{bbox};"
        f"nwr[name][amenity]{bbox};nwr[name][leisure]{bbox};"
        f"nwr[name][building]{bbox};);out meta center geom;"
    )


def historical_protocol(operation, scope, version):
    """Return the recorded legacy protocol, or None when the current one applies."""
    if operation == "onwani" and version in ONWANI_FIELDS:
        return AcquisitionProtocol(version=version, onwani_fields=ONWANI_FIELDS[version])
    if operation == "map" and scope.endswith(":osm") and version in NAMED_POI_OSM_VERSIONS:
        territory = scope.split(":", 1)[0]
        return AcquisitionProtocol(version=version, osm_query=named_poi_osm_query(territory))
    return None


# `map_import.py` at 087241d and 001b65c: a place needed a name (`name:en` or `name`)
# and an amenity, leisure or building tag. Unnamed amenities and shop, tourism and
# transport places arrive with `osm_place_kind` in district-map-v5/osm-api-bootstrap-v2
# (06af8b2). `osm_api_protocol.py` at 001b65c (osm-api-bootstrap-v1) also dropped, before
# mapping, every element other than buildings and named highways, amenities or leisure.
# The replay keeps the current mapping; these rules only say which replayed observations
# the original mapping could not have produced (A15).
def _legacy_named(tags):
    return bool(str(tags.get("name:en") or tags.get("name") or "").strip())


def _legacy_place(tags):
    return _legacy_named(tags) and bool(
        tags.get("amenity") or tags.get("leisure") or tags.get("building")
    )


def _legacy_bootstrap_element(tags):
    return bool(
        tags.get("building")
        or (tags.get("name") and any(tags.get(k) for k in ("highway", "amenity", "leisure")))
    )


def named_place_selection(target, tags):
    return target != "place" or _legacy_place(tags)


def bootstrap_v1_selection(target, tags):
    return _legacy_bootstrap_element(tags) and named_place_selection(target, tags)


LEGACY_OSM_SELECTIONS = {
    **dict.fromkeys(NAMED_POI_OSM_VERSIONS, named_place_selection),
    "osm-api-bootstrap-v1": bootstrap_v1_selection,
}


# `project_import.py` at 123900b (project-details-v1) wrote no project position: the
# source-declared position arrives with `project_locations.py` in 4d2c51f (A15).
def no_position_selection(target, tags):
    return target != "place"


LEGACY_PROJECT_SELECTIONS = {"project-details-v1": no_position_selection}


def legacy_selection(operation, scope, version):
    """`(target, tags) -> bool` for a recorded legacy OSM or project mapping, or None.

    `target` is the map target of an observation, or None for a quarantined element.
    """
    if operation == "osm_bootstrap" or (operation == "map" and scope.endswith(":osm")):
        return LEGACY_OSM_SELECTIONS.get(version)
    if operation == "project_details":
        return LEGACY_PROJECT_SELECTIONS.get(version)
    return None
