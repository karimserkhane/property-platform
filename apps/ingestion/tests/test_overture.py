from property_platform_ingestion.deployments import schedules_for
from property_platform_ingestion.registry import DATASETS, TERRITORIES


def test_parquet_acquisition_filters_and_retains_original_geometry(tmp_path, monkeypatch):
    import io
    import json
    import struct
    from types import SimpleNamespace

    import pyarrow as pa
    import pyarrow.dataset as ds
    import pyarrow.fs as fs
    import pyarrow.parquet as pq

    from property_platform_ingestion.collectors import overture

    path = tmp_path / "places.parquet"

    def place(identity, x):
        return {
            "id": identity,
            "names": {"primary": "Cafe"},
            "taxonomy": {"primary": "cafe", "hierarchy": ["food_and_drink", "cafe"]},
            "confidence": 0.99,
            "operating_status": "open",
            "websites": ["https://example.org"],
            "sources": [{"dataset": "meta", "license": "CDLA-Permissive-2.0"}],
            "bbox": {"xmin": x, "xmax": x, "ymin": 24.5, "ymax": 24.5},
            "geometry": struct.pack("<BIdd", 1, 1, x, 24.5),
        }

    pq.write_table(pa.Table.from_pylist([place("inside", 54.4), place("outside", 55.0)]), path)
    asset = "s3://" + overture.PREFIX + "test.parquet"
    index = pa.Table.from_pylist(
        [
            {
                "collection": "place",
                "type": "Feature",
                "bbox": {"xmin": 54.3, "xmax": 55.1, "ymin": 24.4, "ymax": 24.6},
                "assets": {"aws": {"alternate": {"s3": {"href": asset}}}},
            }
        ]
    )
    buffer = io.BytesIO()
    pq.write_table(index, buffer)

    class HTTP:
        def __init__(self, urls):
            assert urls == [overture.STAC_URL]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def fetch(self, *args, **kwargs):
            return SimpleNamespace(http_status=200, payload=buffer.getvalue())

    original_dataset = ds.dataset

    def dataset(paths, **kwargs):
        assert paths == [asset.removeprefix("s3://")]
        return original_dataset(str(path), format="parquet")

    monkeypatch.setattr(overture, "SourceHTTP", HTTP)
    monkeypatch.setattr(fs, "S3FileSystem", lambda **kwargs: fs.LocalFileSystem())
    monkeypatch.setattr(ds, "dataset", dataset)
    payload, receipt = overture.acquire_places("al-reem-island")
    result = json.loads(payload)
    assert [row["id"] for row in result["rows"]] == ["inside"]
    assert result["rows"][0]["geometry_wkb"] == place("inside", 54.4)["geometry"].hex()
    assert receipt["acquisition_method"] == "overture_parquet_extract"


def test_overture_deployments_are_bounded_and_preserve_weekend_activation_policy():
    rows = [row for row in DATASETS if row.name.endswith("places-overture")]
    assert len(rows) == len(TERRITORIES)
    assert {row.parameters["territory"] for row in rows} == set(TERRITORIES)
    for row in rows:
        assert row.parameters["layer"] == "overture"
        assert row.cron.endswith("* * 0")
        assert schedules_for(row, None)[0].active is False
