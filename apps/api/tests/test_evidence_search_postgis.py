"""Evidence search index rebuilt from published dossiers on real PostgreSQL (E01)."""

import os

import pytest
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Evidence search requires PostGIS", allow_module_level=True)

from test_project_directory_postgis import ingest_baccarat  # noqa: E402

from property_platform.modules.evidence.models import (  # noqa: E402
    EvidenceSearchEntry,
    HistoryExclusion,
    ProjectSnapshot,
    RowRevision,
)
from property_platform.modules.evidence.search.index import (  # noqa: E402
    rebuild_search_index,
    search_claims,
)

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def test_published_statements_are_found_with_their_evidence():
    ingest_baccarat()
    result = rebuild_search_index(actor="search-test", run_key="first")
    assert result["status"] == "succeeded"
    assert result["summary"]["projects"] == 1
    assert result["summary"]["added"] == result["summary"]["statements"] > 0

    rows = search_claims("penthouse")
    assert rows and rows[0]["kind"] == "typologies"
    assert rows[0]["project"]["slug"] == "baccarat-residences-saadiyat"
    assert rows[0]["source"]["url"].startswith("https://")
    assert rows[0]["source"]["content_sha256"]
    # Project words narrow a query; a word nowhere in the dossier finds nothing.
    assert search_claims("BACCARAT penth")
    assert search_claims("baccarat nonexistentword") == []
    assert search_claims("") == []


def test_a_rebuild_keeps_unchanged_statements_and_is_idempotent_per_run():
    ingest_baccarat()
    rebuild_search_index(actor="search-test", run_key="first")
    keys = set(EvidenceSearchEntry.objects.values_list("claim_key", "ingested_at"))
    journals = RowRevision.objects.filter(table_name="evidence_search_entry").count()

    second = rebuild_search_index(actor="search-test", run_key="second")
    assert second["summary"]["added"] == second["summary"]["removed"] == 0
    assert set(EvidenceSearchEntry.objects.values_list("claim_key", "ingested_at")) == keys
    assert RowRevision.objects.filter(table_name="evidence_search_entry").count() == journals
    assert rebuild_search_index(actor="search-test", run_key="second") == {
        "status": "succeeded",
        "summary": second["summary"],
    }


def test_a_withdrawn_project_leaves_the_index_and_its_answers():
    ingest_baccarat()
    rebuild_search_index(actor="search-test", run_key="first")
    for snapshot in ProjectSnapshot.objects.select_related("project", "capture"):
        HistoryExclusion.objects.get_or_create(
            dataset=f"project:{snapshot.project.slug}",
            record_key=snapshot.capture.url,
            active=True,
            defaults={"capture": snapshot.capture, "reason": "test", "actor": "search-test"},
        )
    # Answers stop at once, before the next rebuild removes the rows.
    assert search_claims("penthouse") == []
    result = rebuild_search_index(actor="search-test", run_key="after-withdrawal")
    assert result["summary"]["statements"] == 0
    assert result["summary"]["removed"] > 0
    assert not EvidenceSearchEntry.objects.exists()


def test_the_preview_route_answers_with_each_statement_and_its_evidence(client):
    ingest_baccarat()
    rebuild_search_index(actor="search-test", run_key="first")
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get("/api/v1/preview/evidence-search", {"q": "penthouse"})
        assert response.status_code == 200
        items = response.json()["items"]
        assert items and items[0]["kind"] == "typologies"
        assert items[0]["project"]["slug"] == "baccarat-residences-saadiyat"
        assert items[0]["source"]["url"].startswith("https://")
        assert items[0]["claim_key"] == search_claims("penthouse")[0]["claim_key"]
        other = client.get(
            "/api/v1/preview/evidence-search", {"q": "penthouse", "territory": "al-reem-island"}
        )
        assert other.json() == {"items": []}
        first = client.get("/api/v1/preview/evidence-search", {"q": "penthouse", "limit": 1})
        assert first.json()["items"] == items[:1]
        assert client.get("/api/v1/preview/evidence-search").status_code == 422
        assert client.get("/api/v1/preview/evidence-search", {"q": "x" * 121}).status_code == 422
    with override_settings(DEBUG=False, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        assert client.get("/api/v1/preview/evidence-search", {"q": "penthouse"}).status_code == 403
