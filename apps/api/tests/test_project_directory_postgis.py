"""Portfolio facts, candidate audit and directory checks on real PostgreSQL."""

import base64
import hashlib
import json
import os
from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Project directory requires PostGIS", allow_module_level=True)

from property_platform.modules.evidence import project_discovery, project_protocol  # noqa: E402
from property_platform.modules.evidence.models import ProjectSourceCandidate  # noqa: E402
from property_platform.modules.evidence.project_import import import_project_details  # noqa: E402
from property_platform.modules.evidence.project_queries import project_directory  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def receipt(url, payload):
    now = timezone.now() - timedelta(seconds=1)
    return {
        "url": url,
        "payload": base64.b64encode(payload).decode(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "http_status": 200,
        "fetched_at": now.isoformat(),
        "fetched_started_at": now.isoformat(),
    }


def ingest_baccarat():
    definition = project_protocol.project_registry("saadiyat-island:baccarat-residences-saadiyat")[
        0
    ]
    api = {
        "data": {
            "communityId": definition["record_id"],
            "projectName": definition["name"],
            "communityLocation": "Saadiyat Island",
            "totalUnits": 78,
            "completionDate": "2029-08-31",
            "unitTypes": ["Apartment", "Penthouse"],
            "bedrooms": ["2", "4"],
        }
    }
    rows = [
        receipt(
            source["url"],
            json.dumps(api).encode()
            if source["parser"] == "aldar_project_v1"
            else b"<html><h1>Baccarat Residences Saadiyat</h1></html>",
        )
        for source in definition["sources"]
    ]
    return (
        definition,
        rows,
        import_project_details(
            rows, territory="saadiyat-island:baccarat-residences-saadiyat", actor="portfolio-test"
        ),
    )


def test_individual_project_scope_is_idempotent_and_never_creates_map_identity(client):
    definition, rows, first = ingest_baccarat()
    assert first["projects"] == 1
    assert (
        import_project_details(
            rows, territory="saadiyat-island:baccarat-residences-saadiyat", actor="portfolio-test"
        )["snapshots"]
        == 0
    )
    directory = project_directory()
    assert len(directory["items"]) == 1
    project = directory["items"][0]
    assert project["slug"] == definition["slug"]
    assert project["has_map_identity"] is False
    assert project_directory("al-reem-island")["items"] == []
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        assert (
            client.get("/api/v1/preview/projects?territory=saadiyat-island").json()["items"][0][
                "name"
            ]
            == definition["name"]
        )
        assert client.get("/api/v1/preview/projects?territory=dubai").status_code == 422
    with override_settings(DEBUG=False, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        assert client.get("/api/v1/preview/projects").status_code == 403


def test_discovered_unknown_project_stays_audited_and_outside_canonical_directory():
    definition, _, _ = ingest_baccarat()
    scope = "saadiyat-island:aldar-saadiyat"
    catalogue = project_discovery.catalogue_for(scope)
    items = [
        {"communityId": definition["record_id"], "projectName": definition["name"]},
        {"communityId": "a22J7000000QNOZXX4", "projectName": "Unreviewed Project"},
    ]
    rows = [
        receipt(catalogue["url"], json.dumps({"data": {"total": 2, "communities": items}}).encode())
    ]
    run = project_discovery.import_catalogue(rows, scope=scope, actor="portfolio-test")
    assert run.summary["registered"] == run.summary["pending_review"] == 1
    unknown = ProjectSourceCandidate.objects.get(status="pending_review")
    assert unknown.project_id is None
    assert unknown.capture.content_sha256 == rows[0]["sha256"]
    assert unknown.territory_scope == "saadiyat-island"
    assert unknown.capture.fetched_at < unknown.ingested_at
    assert len(project_directory()["items"]) == 1
