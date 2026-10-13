"""Reviewed acquisition scopes. Configuration is never taken from arbitrary URLs/SQL."""

from dataclasses import dataclass

DEFAULT_TERRITORY = "al-reem-island"


@dataclass(frozen=True)
class CollectionProfile:
    territory: str
    slug: str
    name: str
    district_name: str
    district_id: int
    osm_bounds: tuple[float, float, float, float]
    reference_registry: str
    presentation_registry: str
    media_registry: str

    @property
    def parcel_namespace(self):
        return f"dmt:onwani:smarthub:plot:adm:{self.slug}"

    @property
    def parcel_where(self):
        return f"DISTRICTENG = '{self.district_name}' AND MUNICIPALITYENG = 'ADM'"

    def map_namespace(self, layer):
        if layer not in {"district", "community", "street", "osm"}:
            raise ValueError("Unknown collection layer")
        return f"osm:{self.slug}:osm" if layer == "osm" else f"dmt:onwani:{self.slug}:{layer}"

    def map_layers(self):
        root = "https://onwani.abudhabi.ae/arcgis/rest/services/"
        return {
            "district": (
                root + "MyLand/SMARTHUB/MapServer/1",
                f"NAMEENGLISH='{self.district_name}'",
                "esriGeometryPolygon",
                "OBJECTID,NAMEENGLISH,NAMEARABIC,DISTRICTID",
            ),
            "community": (
                root + "MyLand/SMARTHUB/MapServer/2",
                f"DISTRICTID='{self.district_id}' "
                f"AND UPPER(DISTRICTNAMEENG)='{self.district_name}'",
                "esriGeometryPolygon",
                "OBJECTID,COMMUNITYNAMEENG,COMMUNITYNAMEARA,DISTRICTID",
            ),
            "street": (
                root + "Onwani/UDM_AddressingLayers/MapServer/2",
                f"UPPER(DISTRICT_EN)='{self.district_name}'",
                "esriGeometryPolyline",
                "OBJECTID,ROADNAME_EN,ROADNAME_AR,NAME_EN,NAME_AR,ROADTYPE_EN,DISTRICT_EN",
            ),
        }

    @property
    def osm_query(self):
        west, south, east, north = self.osm_bounds
        bbox = f"({south},{west},{north},{east})"
        return (
            "[out:json][timeout:45];("
            f"way[building]{bbox};way[highway][name]{bbox};"
            f"nwr[name][amenity]{bbox};nwr[name][leisure]{bbox};"
            f"nwr[name][building]{bbox};);out meta center geom;"
        )


COLLECTIONS = {
    "al-reem-island": CollectionProfile(
        "al-reem-island",
        "reem",
        "Al Reem Island",
        "AL REEM ISLAND",
        57,
        (54.3886, 24.4707, 54.4273, 24.5177),
        "project_sources.json",
        "property_presentations.json",
        "property_media.json",
    ),
    "saadiyat-island": CollectionProfile(
        "saadiyat-island",
        "saadiyat",
        "Saadiyat Island",
        "AL SAADIYAT ISLAND",
        1347,
        (54.386, 24.4886, 54.4812, 24.6019),
        "saadiyat_project_sources.json",
        "saadiyat_property_presentations.json",
        "saadiyat_property_media.json",
    ),
}


def collection_for(territory=DEFAULT_TERRITORY):
    try:
        return COLLECTIONS[territory]
    except (KeyError, TypeError) as exc:
        raise ValueError("Unregistered collection territory") from exc
