from typing import get_args

import pytest

from property_platform.modules.publication.uses import UseType, use_types


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("School", ["school"]),
        ("Masjed", ["mosque"]),
        ("commercial/retialTrade", ["retail"]),
        ("residentialCommercial", ["commercial", "housing"]),
        ("BusStationRapidTransportation", ["bus_station"]),
        ("Temporary Rail Land", ["rail"]),
        ("ProjectLimits", ["project_perimeter"]),
        ("Distribution Substation", ["infrastructure"]),
        ("Parking", ["parking"]),
        ("Trail", []),
        ("Warehouse", []),
        ("multiusage", ["mixed_use"]),
        ("Non-Recreational Open Space", ["open_space"]),
        ("residentialVilla", ["villa"]),
        ("", []),
        ("Unmapped original label", []),
    ],
)
def test_published_uses_are_specific_without_overwriting_original(value, expected):
    assert use_types(land_use=value) == expected
    assert all(code in get_args(UseType) for code in expected)


def test_osm_amenity_is_not_lost_behind_generic_building_yes():
    tags = {"building": "yes", "amenity": "school", "name": "Original school"}
    assert use_types(kind="yes", tags=tags) == ["school"]
    assert tags["name"] == "Original school"
    assert use_types(kind="office", tags=tags) == ["school"]


def test_station_and_worship_require_meaningful_source_tags():
    assert use_types(kind="station") == []
    assert use_types(tags={"railway": "station"}) == ["rail_station"]
    assert use_types(tags={"amenity": "place_of_worship"}) == ["worship"]
    assert use_types(tags={"amenity": "place_of_worship", "religion": "muslim"}) == ["mosque"]
    assert use_types(tags={"shop": "supermarket"}) == ["retail"]
    assert use_types(tags={"name": "Mosque School Towers", "private_contact": "Clinic"}) == []
