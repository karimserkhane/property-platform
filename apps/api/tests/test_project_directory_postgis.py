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

from property_platform.modules.evidence import (  # noqa: E402
    orchestration,
    project_discovery,
    project_protocol,
)
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


def test_reviewed_alias_replays_capture_without_erasing_old_decision(monkeypatch):
    definition, _, _ = ingest_baccarat()
    alias = (
        "https://psinv.net/en/projects/abu-dhabi/abu-dhabi-district/saadiyat-island/"
        "reviewed-baccarat-alias-12345"
    )
    scope = "saadiyat-island:psi-saadiyat-island"
    catalogue = project_discovery.catalogue_for(scope)
    body = (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{alias}</loc></url></urlset>"
    ).encode()
    rows = [receipt(catalogue["url"], body)]
    reviewed = {**definition, "url_aliases": []}
    monkeypatch.setattr(project_discovery, "project_registry", lambda _: [reviewed])

    def replay(key):
        return orchestration.execute_import(
            operation="project_discovery",
            scope=scope,
            actor="catalogue-alias-review",
            execution_key=hashlib.sha256(key.encode()).hexdigest(),
            receipt=rows,
        )

    first = replay("before-review")
    assert first["summary"]["pending_review"] == 1
    reviewed["url_aliases"] = [alias]
    second = replay("after-review")
    assert not second["reused"] and second["summary"]["registered"] == 1
    third = replay("same-review")
    assert third["reused"] and third["reused_from"] == second["execution_id"]
    observations = ProjectSourceCandidate.objects.filter(source_url=alias).order_by("id")
    assert list(observations.values_list("status", flat=True)) == ["pending_review", "registered"]
    assert len(set(observations.values_list("capture__content_sha256", flat=True))) == 1
    assert len(set(observations.values_list("capture__fetched_at", flat=True))) == 1


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


def test_directory_search_and_pagination_reach_projects_beyond_the_first_200(client):
    from property_platform.modules.catalog.models import Project
    from property_platform.modules.evidence.models import ProjectSnapshot

    _, _, _ = ingest_baccarat()
    first = ProjectSnapshot.objects.filter(source_role="project").earliest("id")
    added = Project.objects.bulk_create(
        [
            Project(
                slug=f"review-{i:03}",
                name=f"Review {i:03}",
                territory_id="al-reem-island",
                developer=first.project.developer,
                website_url="https://example.com/review",
            )
            for i in range(205)
        ]
    )
    ProjectSnapshot.objects.bulk_create(
        [
            ProjectSnapshot(
                project=project,
                capture=first.capture,
                receipt_key=hashlib.sha256(project.slug.encode()).hexdigest(),
                extractor_version="pagination-test",
                source_role="project",
                title=project.name,
                actor="test-review",
            )
            for project in added
        ]
    )
    first_page = project_directory(limit=200)
    last_page = project_directory(offset=200, limit=200)
    assert first_page["total"] == 206 and first_page["has_more"]
    assert len(last_page["items"]) == 6 and not last_page["has_more"]
    assert len({p["slug"] for p in first_page["items"] + last_page["items"]}) == 206
    assert project_directory(query="Review 204")["items"][0]["slug"] == "review-204"
    assert project_directory("saadiyat-island", query="Review")["total"] == 0
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get("/api/v1/preview/projects", {"q": "Review 204", "limit": 1})
        assert response.status_code == 200 and response.json()["total"] == 1
        for changes in [
            {"limit": 0},
            {"limit": 201},
            {"offset": -1},
            {"offset": 50001},
            {"q": "x" * 121},
        ]:
            assert client.get("/api/v1/preview/projects", changes).status_code == 422
