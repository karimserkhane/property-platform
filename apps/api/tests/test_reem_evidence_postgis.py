import base64
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Evidence integration requires real PostGIS", allow_module_level=True)

from property_platform.modules.evidence.management.commands.import_reem_imagery import (  # noqa: E402
    BASE,
    BBOX,
    SCENES,
)
from property_platform.modules.evidence.models import ImageryScene, IngestionRun, ResearchReference  # noqa: E402
from property_platform.modules.evidence.sources.research_import import (  # noqa: E402
    import_reference,
    page_metadata,
)

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def imagery_receipt():
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jB8sAAAAASUVORK5CYII="
    )
    now = datetime.now(UTC)
    return [
        {
            "url": BASE + identity,
            "bbox": BBOX,
            "render_version": "reem-sentinel-crop-v1",
            "fetched_started_at": (now - timedelta(seconds=1)).isoformat(),
            "fetched_at": now.isoformat(),
            "payload": base64.b64encode(
                json.dumps(
                    {
                        "id": identity,
                        "properties": {"datetime": "2026-06-29T07:00:00Z", "eo:cloud_cover": 4},
                        "assets": {
                            "visual": {
                                "href": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/example.tif"
                            }
                        },
                    }
                ).encode()
            ).decode(),
            "preview": base64.b64encode(png).decode(),
            "preview_sha256": hashlib.sha256(png).hexdigest(),
        }
        for identity in sorted(SCENES)
    ]


def test_immutable_imagery_repeat_and_safe_projection(tmp_path, client):
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(imagery_receipt()), encoding="utf-8")
    for _ in range(2):
        call_command("import_reem_imagery", actor="test", receipt=str(path))
    assert ImageryScene.objects.count() == 2
    assert IngestionRun.objects.count() == 4
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get("/api/v1/preview/imagery")
    assert response.status_code == 200
    item = response.json()[0]
    assert item["image_url"].startswith("data:image/png;base64,")
    assert item["coordinates"][0] == [BBOX[0], BBOX[3]]
    assert not {"actor", "payload", "preview_sha256"} & set(item)


def test_invalid_receipt_rejects_whole_batch_before_database_write(tmp_path):
    from django.core.management.base import CommandError

    rows = imagery_receipt()
    rows[1]["preview_sha256"] = "0" * 64
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(CommandError):
        call_command("import_reem_imagery", actor="test", receipt=str(path))
    assert ImageryScene.objects.count() == IngestionRun.objects.count() == 0


def test_source_title_is_plain_text_not_a_copied_assertion():
    title, markers = page_metadata(
        b"<title>Example &amp; Project</title><script>fake()</script>"
        b'<span data-lat="24.5" data-lng="54.4"></span>'
    )
    assert title == "Example & Project"
    assert markers == [("24.5", "54.4")]


def test_failed_source_remains_a_failed_run_without_invented_reference():
    with patch(
        "property_platform.modules.evidence.sources.research_import.urlopen",
        side_effect=TimeoutError,
    ):
        run = import_reference(
            {"url": "https://reportagegroup.com/example", "label": "Test", "kind": "developer"},
            actor="test",
        )
    assert run.status == "failed"
    assert ResearchReference.objects.count() == 0


def test_reprocess_preserves_receipt_dates_and_retires_known_wrong_marker():
    from django.contrib.gis.geos import Point
    from test_reem_map_postgis import district

    from property_platform.modules.catalog.models import Place
    from property_platform.modules.evidence.models import Capture, MapObservation, Source
    from property_platform.modules.evidence.sources.research_import import reprocess_reference

    district()
    source = Source.objects.create(
        key="research:test",
        name="Reportage",
        url="https://reportagegroup.com/projects/residential-apartments/marlin/",
    )
    now = datetime.now(UTC) - timedelta(days=1)
    oldrun = IngestionRun.objects.create(
        source=source,
        actor="test",
        connector_version="old",
    )
    oldrun.status, oldrun.finished_at = "succeeded", datetime.now(UTC)
    oldrun.save()
    payload = (
        b'<title>Marlin 1 - Reportage</title><div data-lat="24.5" data-lng="54.4">'
        b"<p>Marlin 2 by Reportage</p></div>"
    )
    capture = Capture.objects.create(
        run=oldrun,
        url=source.url,
        payload=payload,
        byte_length=len(payload),
        http_status=200,
        content_sha256=hashlib.sha256(payload).hexdigest(),
        fetched_started_at=now,
        fetched_at=now,
    )
    place = Place.objects.create(
        source_namespace=source.key,
        source_record_id="project-map-marker",
        name="Marlin 1",
        geometry=Point(54.4, 24.5, srid=4326),
    )
    ref = ResearchReference.objects.create(
        capture=capture,
        label="Marlin 1",
        page_title="Marlin 1",
        source_kind="developer",
        available=True,
        place=place,
        mapping_version="v1",
    )
    run = reprocess_reference(ref, actor="test")
    assert run.status == "succeeded"
    place.refresh_from_db()
    assert place.active is False and place.revision == 2
    assert MapObservation.objects.get().action == "retired"
    copied = run.captures.get()
    assert copied.parent_capture_id == capture.pk and copied.fetched_at == capture.fetched_at
    assert copied.acquisition_method == "stored_capture_reprocess"
