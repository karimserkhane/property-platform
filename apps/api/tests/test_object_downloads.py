import io

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber
from test_object_storage import s3_config

from property_platform.object_storage.adapters import LocalStore, S3Store
from property_platform.object_storage.core import StorageError, prepare_asset
from property_platform.object_storage.downloads import (
    UnsatisfiableRange,
    describe_object,
    download_range,
    open_object,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, (0, 9, False)),
        ("bytes=2-5", (2, 5, True)),
        ("bytes=8-", (8, 9, True)),
        ("bytes=-3", (7, 9, True)),
        ("bytes=0-99", (0, 9, True)),
    ],
)
def test_single_range_and_seek_semantics(value, expected):
    span = download_range(value, 10)
    assert (span.start, span.end, span.partial) == expected


@pytest.mark.parametrize(
    "value",
    [
        "bytes=10-",
        "bytes=8-2",
        "bytes=-0",
        "bytes=-",
        "bytes=0-1,4-5",
        "items=1-3",
        "bytes=" + "9" * 100 + "-",
    ],
)
def test_invalid_ranges_fail_without_reading_body(value):
    with pytest.raises(UnsatisfiableRange):
        download_range(value, 10)


def test_local_stream_checks_integrity_and_closes_on_seek_and_disconnect(tmp_path):
    payload = b"\x00\x00\x00\x18ftypmp42" + b"a" * 200000
    store = LocalStore(tmp_path)
    with prepare_asset(io.BytesIO(payload), "video/mp4") as asset:
        receipt = store.put(asset)
    describe_object(store, receipt)
    stream = open_object(store, receipt, download_range("bytes=7-21", receipt.size))
    assert b"".join(stream) == payload[7:22]
    assert stream.handle.closed
    stream = open_object(store, receipt, download_range(None, receipt.size))
    assert len(next(iter(stream))) <= 65536
    stream.close()
    store._path(receipt.key).write_bytes(b"b" * len(payload))
    with pytest.raises(StorageError):
        describe_object(store, receipt)


def test_s3_head_and_range_validate_provider_metadata_and_close_socket(tmp_path):
    client = boto3.client(
        "s3",
        region_name="auto",
        endpoint_url="https://example.r2.cloudflarestorage.com",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    store = S3Store(s3_config(tmp_path), client=client)
    with prepare_asset(io.BytesIO(b"%PDF-1.7 original"), "application/pdf") as asset:
        from property_platform.object_storage.core import ObjectReceipt

        receipt = ObjectReceipt(
            "s3",
            store.namespace,
            store.bucket,
            asset.key,
            asset.sha256,
            asset.size,
            asset.mime_type,
        )
    metadata = {"ContentType": receipt.mime_type, "Metadata": {"sha256": receipt.sha256}}
    body = io.BytesIO(b"PDF")
    with Stubber(client) as stub:
        stub.add_response(
            "head_object",
            {**metadata, "ContentLength": receipt.size},
            {"Bucket": store.bucket, "Key": receipt.key},
        )
        stub.add_response(
            "get_object",
            {
                **metadata,
                "ContentLength": 3,
                "ContentRange": f"bytes 1-3/{receipt.size}",
                "Body": StreamingBody(body, 3),
            },
            {"Bucket": store.bucket, "Key": receipt.key, "Range": "bytes=1-3"},
        )
        describe_object(store, receipt)
        stream = open_object(store, receipt, download_range("bytes=1-3", receipt.size))
        assert b"".join(stream) == b"PDF" and body.closed
        stub.assert_no_pending_responses()
