from property_platform.modules.catalog.territories import TERRITORIES, TERRITORY_BY_ID
from property_platform.modules.publication.coverage import (
    PROFILES,
    map_source_namespaces,
    member_territories,
    navigation_registry,
    reference_source_keys,
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


def test_whole_area_only_composes_the_two_reviewed_collection_scopes():
    from property_platform.modules.evidence.collection_profiles import COLLECTIONS

    members = ("al-reem-island", "saadiyat-island")
    assert member_territories("abu-dhabi") == members
    assert member_territories("dubai") == ()
    # Navigation aggregation must not create or activate an emirate-wide acquisition.
    assert "abu-dhabi" not in COLLECTIONS
    assert set(PROFILES["abu-dhabi"].parcel_namespaces) == {
        key for member in members for key in PROFILES[member].parcel_namespaces
    }
    assert set(map_source_namespaces("abu-dhabi")) == {
        key for member in members for key in map_source_namespaces(member)
    }
    assert set(reference_source_keys(PROFILES["abu-dhabi"])) == {
        key for member in members for key in reference_source_keys(PROFILES[member])
    }
