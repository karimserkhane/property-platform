import json
from uuid import uuid4

import pytest

from property_platform_ingestion.media_files import manifest_files


def test_private_manifest_accepts_only_existing_files_in_intake_directory(tmp_path):
    (tmp_path / "media").mkdir()
    (tmp_path / "media" / "owned.mp4").write_bytes(b"test")
    identity = str(uuid4())
    (tmp_path / "files.json").write_text(
        json.dumps([{"media_id": identity, "filename": "owned.mp4"}])
    )
    assert manifest_files(tmp_path, "files.json") == [(identity, tmp_path / "media" / "owned.mp4")]


@pytest.mark.parametrize(
    "filename",
    ["../secret", "/etc/secret", "https://example.org/a.mp4", "C:/secret", "missing.mp4"],
)
def test_private_manifest_rejects_paths_urls_and_missing_files(tmp_path, filename):
    (tmp_path / "files.json").write_text(
        json.dumps([{"media_id": str(uuid4()), "filename": filename}])
    )
    with pytest.raises(ValueError):
        manifest_files(tmp_path, "files.json")


def test_media_intake_directory_cannot_be_a_symlink_outside_storage(tmp_path):
    outside = tmp_path.parent / "outside-media-files"
    outside.mkdir(exist_ok=True)
    (outside / "owned.mp4").write_bytes(b"test")
    try:
        (tmp_path / "media").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Host does not permit symlinks")
    (tmp_path / "files.json").write_text(
        json.dumps([{"media_id": str(uuid4()), "filename": "owned.mp4"}])
    )
    with pytest.raises(ValueError, match="escapes"):
        manifest_files(tmp_path, "files.json")
