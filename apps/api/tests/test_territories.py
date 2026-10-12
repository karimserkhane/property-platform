from property_platform.modules.catalog.territories import TERRITORIES, TERRITORY_BY_ID
from property_platform.modules.publication.coverage import PROFILES, navigation_registry


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
    assert registry["default_territory_id"] == "al-reem-island"
    assert {item["id"] for item in registry["territories"] if item["queryable"]} == set(PROFILES)
    assert "parcel_count" not in registry["territories"][0]
