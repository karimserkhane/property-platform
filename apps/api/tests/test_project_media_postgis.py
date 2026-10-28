import os

import pytest
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Project media requires real PostGIS", allow_module_level=True)

from test_projects_postgis import project_input  # noqa: E402,F401,F811

from property_platform.modules.evidence.models import Capture, ProjectMedia  # noqa: E402
from property_platform.modules.evidence.projects.project_import import import_project_details  # noqa: E402
from property_platform.modules.evidence.projects.project_media_storage import (  # noqa: E402
    approve_project_media,
    attach_project_media_file,
)
from property_platform.object_storage.core import StorageError  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def test_operator_video_intake_is_external_idempotent_and_requires_distinct_rights(
    project_input,  # noqa: F811
    tmp_path,
    client,  # noqa: F811
):
    definition, rows, parsed = project_input
    parsed["media"][0].update(
        mime_type="video/mp4", source_url="https://bloomholding.com/example.mp4"
    )
    import_project_details(
        rows, territory=f"{definition['territory_id']}:{definition['slug']}", actor="test"
    )
    media = ProjectMedia.objects.first()
    payload = b"\x00\x00\x00\x18ftypmp42" + b"test-video" * 500
    path = tmp_path / "owned.mp4"
    path.write_bytes(payload)
    url = f"/api/v1/preview/project-media/{media.id}"
    with override_settings(
        DEBUG=True,
        PROPERTY_PLATFORM_PARCEL_PREVIEW=True,
        MEDIA_STORAGE={"local_root": str(tmp_path / "objects")},
    ):
        assert client.get(url).status_code == 404
        capture = attach_project_media_file(media.id, path, actor="test")
        assert capture.payload is None and capture.primary_object_id is not None
        assert capture.http_status is None and capture.acquisition_method == "manual_media_file"
        assert attach_project_media_file(media.id, path, actor="test").id == capture.id
        assert client.get(url).status_code == 404
        with pytest.raises(StorageError):
            approve_project_media(
                media.id,
                rights_capture_id=capture.id,
                actor="test",
                author="Owner",
                licence_code="explicit_permission",
                licence_url="https://example.org/grant",
            )
        proof = (
            Capture.objects.exclude(pk=capture.pk)
            .exclude(pk=media.snapshot.terms_capture_id)
            .first()
        )
        approve_project_media(
            media.id,
            rights_capture_id=proof.id,
            actor="test",
            author="Owner",
            licence_code="explicit_permission",
            licence_url="https://example.org/grant",
        )
        head = client.head(url)
        assert head.status_code == 200 and head.content == b""
        assert int(head.headers["Content-Length"]) == len(payload)
        partial = client.get(url, headers={"Range": "bytes=9-30"})
        assert partial.status_code == 206
        assert b"".join(partial.streaming_content) == payload[9:31]
        assert partial.headers["Content-Range"] == f"bytes 9-30/{len(payload)}"
        assert client.get(url, headers={"Range": "bytes=999999-"}).status_code == 416
        whole = client.get(url, headers={"Range": "bytes=1-2", "If-Range": '"stale"'})
        assert whole.status_code == 200 and b"".join(whole.streaming_content) == payload
        proof.run.status = "failed"
        proof.run.save(update_fields=["status"])
        assert client.get(url).status_code == 404
    with override_settings(DEBUG=False):
        assert client.get(url).status_code == 403
