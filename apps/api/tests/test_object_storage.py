import io
from dataclasses import replace

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import ANY, Stubber

from property_platform.object_storage.adapters import LocalStore, S3Store
from property_platform.object_storage.core import (
    StorageConfig,
    StorageError,
    prepare_asset,
    validate_key,
)

JPEG = b"\xff\xd8\xff\xdbtest-original"


def s3_config(tmp_path, **changes):
    return replace(
        StorageConfig(
            backend="s3",
            local_root=str(tmp_path),
            endpoint_url="https://account.r2.cloudflarestorage.com",
            bucket="platform-originals",
            access_key_id="test-key",
            secret_access_key="test-secret",
        ),
        **changes,
    )


def client():
    # Explicit fake credentials prevent any credential discovery or metadata network access.
    return boto3.client(
        "s3",
        region_name="auto",
        endpoint_url="https://account.r2.cloudflarestorage.com",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
    )


@pytest.mark.parametrize(
    "name",
    [
        "../private",
        "/absolute",
        "C:/secret",
        "objects/../secret",
        "https://host/a.jpg",
        "objects/sha256/ab/" + "a" * 64 + ".html",
    ],
)
def test_keys_cannot_be_paths_urls_or_active_html(name):
    with pytest.raises(StorageError):
        validate_key(name)


@pytest.mark.parametrize(
    "body,mime",
    [
        (JPEG, "image/jpeg"),
        (b"\x89PNG\r\n\x1a\nimage", "image/png"),
        (b"RIFFxxxxWEBPimage", "image/webp"),
        (b"%PDF-1.7 document", "application/pdf"),
        (b"\x00\x00\x00\x18ftypmp42video", "video/mp4"),
        (b"\x1aE\xdf\xa3webm", "video/webm"),
        (b"glTF\x02\x00\x00\x00model", "model/gltf-binary"),
    ],
)
def test_each_supported_format_round_trips_with_a_bounded_integrity_check(tmp_path, body, mime):
    store = LocalStore(tmp_path)
    with prepare_asset(io.BytesIO(body), mime) as asset:
        first = store.put(asset)
        second = store.put(asset)
    assert first == second
    assert store.read(first, max_bytes=len(body)) == body
    assert len(list(tmp_path.rglob(first.key.split("/")[-1]))) == 1
    with pytest.raises(StorageError, match="budget"):
        store.read(first, max_bytes=len(body) - 1)
    tmp_path.joinpath(first.key).write_bytes(b"tampered")
    with pytest.raises(StorageError, match="integrity"):
        store.read(first)
    with prepare_asset(io.BytesIO(body), mime) as asset:
        with pytest.raises(StorageError, match="integrity"):
            store.put(asset)  # A bad existing object is never overwritten silently.


@pytest.mark.parametrize(
    "body,mime,budget",
    [
        (b"<script>bad</script>", "image/jpeg", 100),
        (JPEG, "image/svg+xml", 100),
        (b"", "application/pdf", 100),
        (JPEG, "image/jpeg", 2),
    ],
)
def test_invalid_and_oversized_inputs_are_rejected_before_writes(body, mime, budget):
    with pytest.raises(StorageError), prepare_asset(io.BytesIO(body), mime, max_bytes=budget):
        pytest.fail("Input must be rejected")


def test_local_symbolic_link_cannot_read_outside_the_media_volume(tmp_path):
    store = LocalStore(tmp_path / "media")
    with prepare_asset(io.BytesIO(JPEG), "image/jpeg") as asset:
        receipt = store.put(asset)
    path = store.root.joinpath(receipt.key)
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(JPEG)
    path.unlink()
    try:
        path.symlink_to(outside)
    except OSError:
        pytest.skip("Host does not allow symlinks")
    with pytest.raises(StorageError, match="Symbolic"):
        store.read(receipt)


def test_r2_conditional_put_reconciles_a_prior_success_by_hash_not_etag(tmp_path):
    sdk = client()
    store = S3Store(s3_config(tmp_path), client=sdk)
    with prepare_asset(io.BytesIO(JPEG), "image/jpeg") as asset, Stubber(sdk) as stub:
        parameters = {
            "Bucket": "platform-originals",
            "Key": asset.key,
            "Body": ANY,
            "ContentLength": len(JPEG),
            "ContentType": "image/jpeg",
            "Metadata": {"sha256": asset.sha256},
            "IfNoneMatch": "*",
            "CacheControl": "private, no-store",
        }
        stub.add_client_error(
            "put_object", "PreconditionFailed", http_status_code=412, expected_params=parameters
        )
        stub.add_response(
            "get_object",
            {
                "Body": StreamingBody(io.BytesIO(JPEG), len(JPEG)),
                "ContentLength": len(JPEG),
                "ContentType": "image/jpeg",
                "Metadata": {"sha256": asset.sha256},
                "ETag": '"not-a-sha256"',
            },
            {"Bucket": "platform-originals", "Key": asset.key},
        )
        receipt = store.put(asset)
        assert receipt.sha256 == asset.sha256
        stub.assert_no_pending_responses()


def test_s3_failure_is_sanitized_and_never_records_a_success(tmp_path):
    sdk = client()
    with prepare_asset(io.BytesIO(JPEG), "image/jpeg") as asset, Stubber(sdk) as stub:
        stub.add_client_error(
            "put_object", "AccessDenied", "secret-provider-detail", http_status_code=403
        )
        with pytest.raises(StorageError, match="^S3 media write failed$"):
            S3Store(s3_config(tmp_path), client=sdk).put(asset)


@pytest.mark.parametrize(
    "changes",
    [
        {"endpoint_url": "http://account.example"},
        {"endpoint_url": "https://u:secret@host/"},
        {"access_key_id": ""},
        {"namespace": "local"},
        {
            "publication_enabled": True,
            "public_bucket": "platform-originals",
            "public_base_url": "https://media.example",
        },
        {
            "publication_enabled": True,
            "public_bucket": "public-media",
            "public_base_url": "https://example.r2.dev",
        },
    ],
)
def test_cloud_config_fails_closed_without_explicit_private_public_separation(tmp_path, changes):
    with pytest.raises(StorageError):
        s3_config(tmp_path, **changes).validate()
