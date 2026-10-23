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
