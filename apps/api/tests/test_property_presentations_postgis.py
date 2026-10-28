import os
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Property presentations require real PostGIS", allow_module_level=True)

from django.contrib.gis.geos import MultiPolygon, Polygon  # noqa: E402
from django.db import IntegrityError, connection, transaction  # noqa: E402
from test_property_protocol import receipt  # noqa: E402

from property_platform.modules.catalog.models import Building  # noqa: E402
from property_platform.modules.evidence.models import (
    Capture,
    IngestionRun,
    PropertyMedia,
    PropertyPresentation,
)  # noqa: E402
from property_platform.modules.evidence.projects.property_import import import_presentations  # noqa: E402
from property_platform.modules.evidence.projects.queries import property_presentations  # noqa: E402

# Agency, Aldar and relation fixtures use sites whose rights withhold them (A19); their
# replay mechanics remain tested here, what rights hide is in test_source_rights_postgis.py.
pytestmark = [
    pytest.mark.postgis,
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("unrestricted_sources"),
]


def sample():
    building = Building.objects.create(
        source_namespace="test:osm",
        source_record_id="way/1",
        name="Reviewed Tower",
        kind="residential",
        geometry=MultiPolygon(Polygon.from_bbox((54.39, 24.49, 54.391, 24.491)), srid=4326),
    )
    photo = {
        "image_url": "https://upload.wikimedia.org/example.jpg",
        "source_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
        "author": "Photographer",
        "licence_code": "CC-BY-3.0",
        "licence_url": "https://creativecommons.org/licenses/by/3.0/",
        "caption": "Historical photo of Reviewed Tower",
        "language": "en",
        "taken_on": "2011-03-21",
        "mime_type": "image/jpeg",
    }
    row = {
        "target": "building",
        "namespace": building.source_namespace,
        "record_id": building.source_record_id,
        "display_name": building.name,
        "publisher_name": "Aldar",
        "developer_name": "Aldar",
        "website_url": "https://www.aldar.com/example",
        "source_url": "https://www.aldar.com/example",
        "required_terms": ["Reviewed Tower"],
        "summary": "Reviewed description",
        "language": "en",
        "photo_key": "example",
    }
    receipts = [
        receipt(row["source_url"], b"Reviewed Tower by Aldar"),
        receipt(photo["source_url"], b"Photographer https://creativecommons.org/licenses/by/3.0/"),
        receipt(photo["image_url"], b"\xff\xd8\xff\xdblicensed-photo-test"),
    ]
    return building, row, photo, receipts


def test_reviewed_profile_keeps_identity_history_and_source_dates(client):
    building, row, photo, receipts = sample()
    for _ in range(2):
        import_presentations(
            receipts, actor="test-reviewer", profiles=[row], photos={"example": photo}
        )
    building.refresh_from_db()
    assert building.revision == 1
    assert PropertyPresentation.objects.count() == PropertyMedia.objects.count() == 2
    assert Capture.objects.count() == 6
    with CaptureQueriesContext(connection) as queries:
        data = property_presentations("building", [building.id])[str(building.id)]
    assert all('"payload"' not in query["sql"] for query in queries)
    assert data["developer"] == "Aldar"
    assert data["media"][0]["author"] == "Photographer"
    assert not {"payload", "actor", "review_version"} & data.keys()
    assert not property_presentations("street", [building.id])
    media = PropertyMedia.objects.order_by("-ingested_at").first()
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get(f"/api/v1/preview/property-media/{media.id}")
    assert response.status_code == 200
    assert response["Content-Type"] == "image/jpeg"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response.content == bytes(media.capture.payload)
    with override_settings(DEBUG=False, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        assert client.get(f"/api/v1/preview/property-media/{media.id}").status_code == 403
    media.display_allowed = False
    media.save(update_fields=["display_allowed"])
    assert property_presentations("building", [building.id])[str(building.id)]["media"] == []
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        assert client.get(f"/api/v1/preview/property-media/{media.id}").status_code == 404


def test_missing_licence_rejects_batch_before_any_write():
    _, row, photo, receipts = sample()
    receipts[1] = receipt(photo["source_url"], b"Photographer but no licence")
    with pytest.raises(ValueError, match="author/licence"):
        import_presentations(receipts, actor="test", profiles=[row], photos={"example": photo})
    assert (
        IngestionRun.objects.count()
        == Capture.objects.count()
        == PropertyPresentation.objects.count()
        == 0
    )


def test_transaction_rolls_back_partial_acquisition():
    _, row, photo, receipts = sample()
    with patch.object(PropertyMedia.objects, "create", side_effect=ValueError("bad media")):
        with pytest.raises(ValueError):
            import_presentations(receipts, actor="test", profiles=[row], photos={"example": photo})
    assert (
        IngestionRun.objects.count()
        == Capture.objects.count()
        == PropertyPresentation.objects.count()
        == 0
    )


def test_profile_requires_exactly_one_target_identity():
    _, row, photo, receipts = sample()
    presentation = import_presentations(
        receipts, actor="test", profiles=[row], photos={"example": photo}
    )[0]
    with pytest.raises(IntegrityError), transaction.atomic():
        PropertyPresentation.objects.create(
            capture=presentation.capture,
            display_name="Invalid",
            publisher_name="test",
            website_url=row["website_url"],
            review_version="test",
        )
