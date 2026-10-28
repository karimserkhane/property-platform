import pytest

from property_platform.modules.evidence.maps.map_sources import coordinates, decode
from property_platform.modules.evidence.maps.onwani import SourceError
from property_platform.modules.publication.land_use import category


@pytest.mark.parametrize(
    "payload",
    [
        b'{"remark":"timeout"}',
        b'{"error":{}}',
        b'{"exceededTransferLimit":true}',
        b"[]",
        b"invalid",
    ],
)
def test_map_rejects_truncated_or_invalid_snapshots(payload):
    with pytest.raises(SourceError):
        decode(payload)


@pytest.mark.parametrize(
    "points",
    [
        [],
        [[54.4, 24.5]],
        [[54.4, 24.5, 0], [54.41, 24.51]],
        [[float("nan"), 24.5], [54.4, 24.5]],
        [[0, 0], [1, 1]],
    ],
)
def test_map_rejects_unbounded_or_invalid_geometry(points):
    with pytest.raises(SourceError):
        coordinates(points)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Project Limit", "overlay"),
        ("Railway Station", "rail"),
        ("Residential/Commerical", "mixed"),
        ("Townhouse", "residential"),
        ("Public Park", "green"),
        ("School", "public"),
        ("Electrical Station", "tech"),
        ("Parking", "tech"),
        ("Mixed Park", "green"),
        ("busTerminal", "tech"),
        ("ChlorineTreatmentPlant", "tech"),
        ("desalinationPlant", "tech"),
        ("reservoir", "tech"),
        ("tmpTransformer", "tech"),
        ("", "unknown"),
    ],
)
def test_original_land_use_has_explicit_display_category(value, expected):
    assert category(value) == expected
