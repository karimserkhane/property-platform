import numpy as np
import pytest

from property_platform_ingestion.collectors.sentinel_activity import (
    BANDS,
    METHOD_VERSION,
    SceneError,
    change_signal,
    reflectance,
    scene_record,
    select_scenes,
)

ROOT = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/40/R/BN/"
FILES = {"blue": "B02", "green": "B03", "red": "B04", "nir": "B08", "scl": "SCL"}


def feature(identity, when, cloud, tile="MGRS-40RBN"):
    band = {"nodata": 0, "data_type": "uint16", "scale": 0.0001, "offset": -0.1}
    return {
        "id": identity,
        "collection": "sentinel-2-l2a",
        "properties": {"datetime": when, "eo:cloud_cover": cloud, "grid:code": tile},
        "assets": {
            key: {
                "href": f"{ROOT}{identity}/{name}.tif",
                **({} if key == "scl" else {"raster:bands": [band]}),
            }
            for key, name in FILES.items()
        },
    }


def window(value, shape=(10, 10), scl=4):
    return {**{band: np.full(shape, value) for band in BANDS}, "scl": np.full(shape, scl)}


def test_scene_record_keeps_reviewed_assets_and_scaling():
    record = scene_record(feature("S2C_40RBN_20261004_0_L2A", "2026-10-04T06:59:01.123000Z", 0.27))
    assert record["scene_id"] == "S2C_40RBN_20261004_0_L2A"
    assert record["acquired_at"].isoformat() == "2026-10-04T06:59:01.123000+00:00"
    assert record["assets"]["red"] == {
        "href": ROOT + "S2C_40RBN_20261004_0_L2A/B04.tif",
        "scale": 0.0001,
        "offset": -0.1,
    }
    assert record["assets"]["scl"]["scale"] == 1.0


@pytest.mark.parametrize(
    "change",
    [
        lambda item: item.update(collection="sentinel-2-l1c"),
        lambda item: item.update(id="S2C_40RBN_20261004_0_L1C"),
        lambda item: item["assets"]["red"].update(href="https://example.com/B04.tif"),
        lambda item: item["assets"]["nir"].update(href=ROOT + "../B08.tif"),
        lambda item: item["assets"].pop("scl"),
        lambda item: item["properties"].update(datetime="2026-10-04T06:59:01"),
        lambda item: item["properties"].update({"eo:cloud_cover": 101}),
        lambda item: item["assets"]["blue"]["raster:bands"][0].update(scale=2),
    ],
)
def test_scene_record_rejects_unreviewed_items(change):
    item = feature("S2C_40RBN_20261004_0_L2A", "2026-10-04T06:59:01Z", 1)
    change(item)
    with pytest.raises(SceneError):
        scene_record(item)


def test_select_scenes_keeps_least_cloudy_per_month_and_tile():
    scenes = select_scenes(
        [
            feature("S2C_40RBN_20261004_0_L2A", "2026-10-04T07:00:00Z", 3.0),
            feature("S2A_40RBN_20261014_0_L2A", "2026-10-14T07:00:00Z", 0.5),
            feature("S2B_40RBN_20260919_0_L2A", "2026-09-19T07:00:00Z", 45.0),
            feature("S2B_40RBN_20260909_0_L2A", "2026-09-09T07:00:00Z", 12.0),
            feature("S2B_40RBP_20260909_0_L2A", "2026-09-09T07:00:00Z", 1.0, "MGRS-40RBP"),
        ]
    )
    assert [row["scene_id"] for row in scenes] == [
        "S2B_40RBN_20260909_0_L2A",
        "S2A_40RBN_20261014_0_L2A",
        "S2B_40RBP_20260909_0_L2A",
    ]


def test_select_scenes_never_falls_back_to_a_cloudy_scene():
    assert select_scenes([feature("S2B_40RBN_20260919_0_L2A", "2026-09-19T07:00Z", 60)]) == []


def test_reflectance_applies_scaling_and_no_data():
    values = reflectance(np.array([[0, 1000, 3000]], dtype=np.uint16), scale=0.0001, offset=-0.1)
    assert np.isnan(values[0, 0])
    assert values[0, 1:] == pytest.approx([0.0, 0.2])


def test_change_signal_measures_the_share_of_changed_pixels():
    before, after = window(0.2), window(0.2)
    for band in BANDS:
        after[band][:5, :] = 0.35
    parcel = np.ones((10, 10), dtype=bool)
    result = change_signal(before, after, parcel)
    assert result == {
        "method_version": METHOD_VERSION,
        "parcel_pixels": 100,
        "clear_pixels": 100,
        "changed_pixels": 50,
        "changed_share": 0.5,
        "median_difference": pytest.approx(0.075),
        "level": "high",
        "status": "measured",
    }


def test_change_signal_ignores_pixels_outside_the_parcel():
    before, after = window(0.2), window(0.2)
    for band in BANDS:
        after[band][:, :2] = 0.5
    parcel = np.zeros((10, 10), dtype=bool)
    parcel[:, 2:] = True
    result = change_signal(before, after, parcel)
    assert (result["changed_pixels"], result["level"]) == (0, "low")


def test_change_signal_refuses_to_measure_through_clouds():
    before, after = window(0.2), window(0.4, scl=9)
    after["scl"][:3, :] = 4
    result = change_signal(before, after, np.ones((10, 10), dtype=bool))
    assert result["status"] == "insufficient_clear_pixels"
    assert result["clear_pixels"] == 30
    assert result["level"] is result["changed_share"] is None


def test_change_signal_excludes_no_data_pixels():
    before, after = window(0.2), window(0.2)
    before["red"][:, :5] = np.nan
    result = change_signal(before, after, np.ones((10, 10), dtype=bool))
    assert result["status"] == "insufficient_clear_pixels"
    assert result["clear_pixels"] == 50


def test_change_signal_requires_one_grid():
    with pytest.raises(ValueError):
        change_signal(window(0.2), window(0.2, shape=(9, 10)), np.ones((10, 10), dtype=bool))
    with pytest.raises(ValueError):
        change_signal(window(0.2), window(0.2), np.zeros((10, 10), dtype=bool))
