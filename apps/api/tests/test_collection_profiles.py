import pytest

from property_platform.modules.evidence import map_sources, onwani
from property_platform.modules.evidence.collection_profiles import collection_for


def test_default_protocol_identity_and_queries_are_preserved():
    profile = collection_for()
    assert profile.parcel_namespace == "dmt:onwani:smarthub:plot:adm:reem"
    assert profile.parcel_where == onwani.WHERE
    assert profile.map_layers() == map_sources.LAYERS
    assert profile.osm_query == map_sources.OSM_QUERY


def test_saadiyat_scope_uses_reviewed_official_district_and_distinct_namespaces():
    profile = collection_for("saadiyat-island")
    assert profile.district_id == 1347
    assert "AL SAADIYAT ISLAND" in profile.parcel_where
    assert "1347" in profile.map_layers()["community"][1]
    assert profile.map_namespace("osm") != collection_for().map_namespace("osm")
    assert "24.6019" in profile.osm_query
    with pytest.raises(ValueError):
        collection_for("arbitrary-area")


def test_saadiyat_feature_cannot_be_imported_as_reem():
    feature = {
        "attributes": {
            "OBJECTID": 9,
            "DISTRICTENG": "AL SAADIYAT ISLAND",
            "MUNICIPALITYENG": "ADM",
        },
        "geometry": {"rings": [[[54.42, 24.54], [54.43, 24.54], [54.42, 24.55], [54.42, 24.54]]]},
    }
    assert onwani.parse_feature(feature, territory="saadiyat-island")["record_id"] == "9"
    with pytest.raises(onwani.SourceError):
        onwani.parse_feature(feature)


def test_all_reference_registries_use_the_supported_source_taxonomy():
    import json
    from importlib.resources import files

    from property_platform.modules.evidence.collection_profiles import COLLECTIONS

    root = files("property_platform.modules.evidence")
    for profile in COLLECTIONS.values():
        rows = json.loads(root.joinpath(profile.reference_registry).read_text(encoding="utf-8"))
        assert len({row["url"] for row in rows}) == len(rows)
        assert all(
            row["kind"] in {"authority", "developer", "broker", "forum", "media"} for row in rows
        )


def test_both_islands_acquire_amenities_without_requiring_a_commercial_name():
    for territory in ("al-reem-island", "saadiyat-island"):
        query = collection_for(territory).osm_query
        assert "nwr[shop]" in query and "nwr[amenity]" in query
        assert "highway=bus_stop" in query and "railway~" in query
        assert "nwr[name][amenity]" not in query
