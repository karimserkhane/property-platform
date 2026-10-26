"""Spatial Parquet extraction using the official STAC index, with bounded streaming."""

import hashlib
import io
import json
import os
from datetime import UTC, datetime

from property_platform.modules.evidence.collection_profiles import collection_for
from property_platform.modules.evidence.maps.overture_protocol import (
    MAX_BYTES,
    MAX_ROWS,
    RELEASE,
    URL,
    decode,
)

from .http import SourceHTTP

STAC_URL = f"https://stac.overturemaps.org/{RELEASE}/collections.parquet"
PREFIX = f"overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/"


def acquire_places(territory):
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.dataset as ds
    import pyarrow.fs as fs
    import pyarrow.parquet as pq

    profile = collection_for(territory)
    west, south, east, north = profile.osm_bounds
    started = datetime.now(UTC)
    with SourceHTTP([STAC_URL]) as transport:
        index = transport.fetch(STAC_URL, allowed_base=STAC_URL, max_bytes=MAX_BYTES)
    if index.http_status != 200:
        raise ValueError("Overture STAC index unavailable")
    table = pq.read_table(io.BytesIO(index.payload))
    intersection = (
        (pc.field("collection") == "place")
        & (pc.field("type") == "Feature")
        & (pc.field("bbox", "xmin") < east)
        & (pc.field("bbox", "xmax") > west)
        & (pc.field("bbox", "ymin") < north)
        & (pc.field("bbox", "ymax") > south)
    )
    assets = table.filter(intersection).column("assets").to_pylist()
    paths = sorted(
        {item["aws"]["alternate"]["s3"]["href"].removeprefix("s3://") for item in assets}
    )
    if not 1 <= len(paths) <= 20 or any(
        not path.startswith(PREFIX) or not path.endswith(".parquet") or ".." in path
        for path in paths
    ):
        raise ValueError("Unexpected or excessive Overture file selection")
    options = dict(anonymous=True, region="us-west-2", connect_timeout=10, request_timeout=30)
    if os.environ.get("AWS_CA_BUNDLE"):
        options["tls_ca_file_path"] = os.environ["AWS_CA_BUNDLE"]
    filesystem = fs.S3FileSystem(**options)
    pa.set_io_thread_count(2)
    dataset = ds.dataset(paths, filesystem=filesystem, format="parquet")
    columns = [
        "id",
        "names",
        "taxonomy",
        "confidence",
        "operating_status",
        "sources",
        "websites",
        "bbox",
        "geometry",
        "__filename",
    ]
    selection = (
        (pc.field("bbox", "xmin") >= west)
        & (pc.field("bbox", "xmax") <= east)
        & (pc.field("bbox", "ymin") >= south)
        & (pc.field("bbox", "ymax") <= north)
    )
    rows, size = [], 0
    for batch in dataset.to_batches(
        columns=columns,
        filter=selection,
        batch_size=256,
        batch_readahead=1,
        fragment_readahead=1,
        use_threads=False,
    ):
        for row in batch.to_pylist():
            row["filename"] = row.pop("__filename")
            row["geometry_wkb"] = row.pop("geometry").hex()
            size += len(json.dumps(row, ensure_ascii=False).encode())
            if len(rows) >= MAX_ROWS or size > MAX_BYTES - 4096:
                raise ValueError("Overture extract exceeds its budget; never publish a truncation")
            rows.append(row)
    payload = json.dumps(
        {
            "release": RELEASE,
            "territory": territory,
            "bounds": list(profile.osm_bounds),
            "index_sha256": hashlib.sha256(index.payload).hexdigest(),
            "files": paths,
            "rows": sorted(rows, key=lambda row: row["id"]),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    decode(payload, territory)
    return payload, {
        "url": URL,
        "http_status": 200,
        "fetched_started_at": started,
        "fetched_at": datetime.now(UTC),
        "etag": "",
        "last_modified_raw": "",
        "acquisition_method": "overture_parquet_extract",
        "timestamp_basis": "collector_clock",
    }
