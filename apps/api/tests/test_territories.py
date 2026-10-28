from property_platform.modules.catalog.territories import TERRITORIES, TERRITORY_BY_ID
from property_platform.modules.publication.coverage import (
    PROFILES,
    collection_bounds,
    emirate_parcel_namespaces,
    map_source_namespaces,
    member_territories,
    navigation_registry,
    reference_source_keys,
    union_bounds,
)


def test_national_navigation_has_seven_emirates_and_an_explicit_pilot():
    assert len(TERRITORY_BY_ID) == len(TERRITORIES)
    emirates = [item for item in TERRITORIES if item.level == "emirate"]
    assert {item.id for item in emirates} == {
        "abu-dhabi",
        "dubai",
        "sharjah",
        "ajman",
        "umm-al-quwain",
        "ras-al-khaimah",
        "fujairah",
    }
    for item in TERRITORIES:
        if item.parent_id:
            assert item.parent_id in TERRITORY_BY_ID
        west, south, east, north = item.bounds
        assert 51 <= west < east <= 57 and 22 <= south < north <= 27
        assert item.name and item.name_ar
    registry = navigation_registry()
    assert registry["default_territory_id"] == "abu-dhabi"
    assert {item["id"] for item in registry["territories"] if item["queryable"]} == set(PROFILES)
    assert "parcel_count" not in registry["territories"][0]


def test_whole_area_composes_the_three_reviewed_collection_scopes():
    from property_platform.modules.evidence.collection_profiles import COLLECTIONS

    members = ("al-reem-island", "saadiyat-island", "al-maryah-island")
    assert member_territories("abu-dhabi") == members
    assert member_territories("dubai") == ()
    # Navigation aggregation must not create or activate an emirate-wide acquisition.
    assert "abu-dhabi" not in COLLECTIONS
    assert {key for member in members for key in PROFILES[member].parcel_namespaces} <= set(
        PROFILES["abu-dhabi"].parcel_namespaces
    )
    assert set(map_source_namespaces("abu-dhabi")) == {
        key for member in members for key in map_source_namespaces(member)
    }
    assert set(reference_source_keys(PROFILES["abu-dhabi"])) == {
        key for member in members for key in reference_source_keys(PROFILES[member])
    }


def test_emirate_parcels_read_every_reviewed_district_without_new_island_identities():
    from property_platform.modules.evidence.maps.onwani import SOURCE_KEY
    from property_platform.modules.evidence.maps.sdi_protocol import district_scopes, namespace

    emirate = PROFILES["abu-dhabi"]
    islands = ("al-reem-island", "saadiyat-island", "al-maryah-island")
    expected = {namespace(scope) for scope in district_scopes()}
    assert set(emirate_parcel_namespaces()) == expected
    assert set(emirate.parcel_namespaces) == expected | {
        key for member in islands for key in PROFILES[member].parcel_namespaces
    }
    assert len(emirate.parcel_namespaces) == len(set(emirate.parcel_namespaces))
    # Island districts of the registry resolve to the namespaces their imports already use.
    for island in islands:
        assert namespace(island) in PROFILES[island].parcel_namespaces
        assert f"ad-sdi:generic-search:plots:adm:{island}" not in emirate.parcel_namespaces
    assert SOURCE_KEY in emirate.parcel_namespaces
    # Parcels reach the emirate; the camera and the context stay on the reviewed islands.
    assert collection_bounds("abu-dhabi") == TERRITORY_BY_ID["abu-dhabi"].bounds
    assert emirate.camera_bounds == union_bounds(PROFILES[key].camera_bounds for key in islands)
    assert collection_bounds("al-reem-island") == TERRITORY_BY_ID["al-reem-island"].bounds
    assert collection_bounds("dubai") is None
