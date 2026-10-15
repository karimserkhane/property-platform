import copy
import os
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Project identity and evidence require real PostGIS", allow_module_level=True)

from django.contrib.gis.geos import MultiPolygon, Polygon  # noqa: E402
from django.db import IntegrityError, connection, transaction  # noqa: E402
from test_property_protocol import receipt  # noqa: E402

from property_platform.modules.catalog.models import Building, Developer, Project  # noqa: E402
from property_platform.modules.evidence import project_protocol  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    IngestionRun,
    ProjectIdentityLink,
    ProjectMedia,
    ProjectSnapshot,
)
from property_platform.modules.evidence.project_import import (  # noqa: E402
    import_project_details,
    revoke_project_link,
)
from property_platform.modules.evidence.project_queries import (  # noqa: E402
    project_detail,
    project_references,
)

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


@pytest.fixture
def project_input():
    definition = project_protocol.project_registry("saadiyat-island")[0]
    for link in definition["identity_links"]:
        Building.objects.create(
            source_namespace=link["namespace"],
            source_record_id=link["record_id"],
            name="Provider building",
            kind="residential",
            geometry=MultiPolygon(Polygon.from_bbox((54.42, 24.54, 54.421, 24.541)), srid=4326),
        )
    rows = [
        receipt(source["url"], b"<html>Source evidence Terms</html>")
        for source in definition["sources"]
    ]
    parsed = {
        "title": definition["name"],
        "parser_version": "fixture-extractor-v1",
        "summary": "",
        "handover": {
            "precision": "quarter",
            "year": 2029,
            "quarter": 2,
            "original_text": "Q2 2029",
            "evidence_pointer": "Handover",
        },
        "total_units": 230,
        "total_units_original": "230 residential units",
        "total_units_pointer": "Programme",
        "typologies": [
            {
                "property_type": "studio",
                "bedrooms": 0,
                "original_text": "Studio",
                "evidence_pointer": "Unit types",
            }
        ],
        "amenities": [
            {
                "code": "swimming-pool",
                "label": "Swimming pool",
                "original_text": "Swimming pool",
                "evidence_pointer": "Amenities",
            }
        ],
        "media": [
            {
                "kind": "video",
                "role": "tour",
                "title": "Official video",
                "mime_type": "text/html",
                "source_url": "https://vimeo.com/1038853770",
                "original_text": "Official video",
                "evidence_pointer": "Video link",
                "rights_status": "reference_only",
            }
        ],
    }

    def extract(project, source, received):
        return None if source["role"] == "terms" else copy.deepcopy(parsed)

    with patch.object(project_protocol, "extract_project_source", side_effect=extract):
        yield definition, rows, parsed


def ingest(rows):
    return import_project_details(rows, territory="saadiyat-island", actor="test-reviewer")


def test_project_import_is_typed_idempotent_and_retains_provider_identities(project_input, client):
    definition, rows, _ = project_input
    first, second = ingest(rows), ingest(rows)
    assert first["snapshots"] == 1 and second["snapshots"] == 0 and second["reused"] == 1
    assert (
        Project.objects.count() == Developer.objects.count() == ProjectSnapshot.objects.count() == 1
    )
    assert ProjectIdentityLink.objects.count() == 3
    assert Capture.objects.count() == 2  # source + captured terms, no binary rehosting
    assert set(Building.objects.values_list("name", flat=True)) == {"Provider building"}
    with CaptureQueriesContext(connection) as queries:
        data = project_detail(definition["slug"])
    assert len(queries) <= 6
    assert all('"payload"' not in query["sql"] for query in queries)
    assert data["handover"]["precision"] == "quarter"
    assert data["handover"]["day"] is None and data["handover"]["month"] is None
    assert data["programme_total"]["value"] == 230
    assert data["typologies"][0]["bedrooms"] == 0
    assert data["media"][0]["delivery_url"] is None
    assert data["media"][0]["rights_status"] == "reference_only"
    assert not {"actor", "receipt_key", "payload", "storage_key"} & data.keys()
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get(f"/api/v1/preview/projects/{definition['slug']}")
        assert response.status_code == 200
        assert response.json()["developer"]["key"] == "bloom-holding"
        assert client.get("/api/v1/preview/projects/not-registered").status_code == 404
    with override_settings(DEBUG=False, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        assert client.get(f"/api/v1/preview/projects/{definition['slug']}").status_code == 403


def test_revoked_project_link_stays_revoked_after_fresh_acquisition(project_input):
    _, rows, _ = project_input
    ingest(rows)
    link = ProjectIdentityLink.objects.order_by("id").first()
    revoke_project_link(link.id, actor="reviewer", reason="Association withdrawn")
    assert str(link.building_id) not in project_references("building", [link.building_id])
    fresh = [receipt(row["url"], b"<html>New source evidence Terms</html>") for row in rows]
    ingest(fresh)
    link.refresh_from_db()
    assert link.active is False and link.revoked_by == "reviewer"
    assert ProjectIdentityLink.objects.count() == 3
    assert ProjectSnapshot.objects.count() == 2


def test_changed_developer_identity_rolls_back_complete_batch(project_input):
    _, rows, _ = project_input
    ingest(rows)
    Developer.objects.update(name="Manually reviewed different name")
    fresh = [receipt(row["url"], b"<html>Fresh source evidence Terms</html>") for row in rows]
    with pytest.raises(ValueError, match="Developer identity changed"):
        ingest(fresh)
    assert ProjectSnapshot.objects.count() == IngestionRun.objects.count() == 1


def test_source_extraction_failure_has_no_partial_database_writes(project_input):
    _, rows, _ = project_input
    with patch.object(
        project_protocol, "extract_project_source", side_effect=ValueError("Changed page")
    ):
        with pytest.raises(ValueError, match="Changed page"):
            ingest(rows)
    assert Project.objects.count() == IngestionRun.objects.count() == Capture.objects.count() == 0


def test_sql_rolls_back_facts_if_media_cannot_be_saved(project_input):
    _, rows, _ = project_input
    with patch.object(ProjectMedia.objects, "create", side_effect=ValueError("Invalid media")):
        with pytest.raises(ValueError, match="Invalid media"):
            ingest(rows)
    assert (
        Project.objects.count() == Capture.objects.count() == ProjectSnapshot.objects.count() == 0
    )


@pytest.mark.parametrize(
    "values",
    [
        {"handover_year": None},
        {"handover_quarter": None},
        {"handover_quarter": 5},
        {"handover_month": 6},
        {"handover_day": 1},
    ],
)
def test_handover_constraints_cannot_invent_precision_or_omit_year(project_input, values):
    _, rows, _ = project_input
    ingest(rows)
    with pytest.raises(IntegrityError), transaction.atomic():
        ProjectSnapshot.objects.update(**values)


def test_media_redistribution_requires_separate_review_and_binary_capture(project_input):
    _, rows, _ = project_input
    ingest(rows)
    with pytest.raises(IntegrityError), transaction.atomic():
        ProjectMedia.objects.update(rights_status="approved")
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        assert project_detail("park-view")["media"][0]["delivery_url"] is None


def test_missing_new_source_fields_preserves_other_source_evidence(project_input):
    _, rows, parsed = project_input
    ingest(rows)
    old = ProjectSnapshot.objects.first()
    # A second independently captured source carries no delivery claim.
    parsed["handover"] = None
    fresh = [receipt(row["url"], b"<html>Offer source Terms</html>") for row in rows]
    ingest(fresh)
    newer = ProjectSnapshot.objects.latest("id")
    newer.capture.url = "https://bloomholding.com/other-project-source"
    newer.capture.save(update_fields=["url"])
    data = project_detail("park-view")
    assert data["handover"]["original_text"] == old.handover_original
    assert data["handover"]["source"]["url"] == rows[0]["url"]
