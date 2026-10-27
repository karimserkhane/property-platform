"""Evidence search index rebuilt from published dossiers on real PostgreSQL (E01)."""

import os

import pytest
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Evidence search requires PostGIS", allow_module_level=True)

from embeddings_fake import FakeService  # noqa: E402
from test_project_directory_postgis import ingest_baccarat  # noqa: E402

from property_platform.modules.evidence.models import (  # noqa: E402
    EvidenceSearchEmbedding,
    EvidenceSearchEntry,
    HistoryExclusion,
    ProjectSnapshot,
    RowRevision,
)
from property_platform.modules.evidence.search import embeddings  # noqa: E402
from property_platform.modules.evidence.search.evaluation import CASES, evaluate  # noqa: E402
from property_platform.modules.evidence.search.index import (  # noqa: E402
    hybrid_claims,
    rebuild_search_index,
    search_claims,
    semantic_claims,
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
        assert other.json() == {"items": [], "mode": "text", "semantic": False}
        first = client.get("/api/v1/preview/evidence-search", {"q": "penthouse", "limit": 1})
        assert first.json()["items"] == items[:1]
        assert client.get("/api/v1/preview/evidence-search").status_code == 422
        assert client.get("/api/v1/preview/evidence-search", {"q": "x" * 121}).status_code == 422
        unknown = client.get("/api/v1/preview/evidence-search", {"q": "penthouse", "mode": "x"})
        assert unknown.status_code == 422
        # Without the optional service, the hybrid mode answers with the full text.
        fallback = client.get(
            "/api/v1/preview/evidence-search", {"q": "penthouse", "mode": "hybrid"}
        ).json()
        assert fallback == {"items": items, "mode": "hybrid", "semantic": False}
    with override_settings(DEBUG=False, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        assert client.get("/api/v1/preview/evidence-search", {"q": "penthouse"}).status_code == 403


def test_vectors_follow_the_index_and_the_pinned_model(monkeypatch):
    ingest_baccarat()
    without = rebuild_search_index(actor="search-test", run_key="no-service")
    assert without["summary"]["embeddings"] == {"status": "not_configured"}
    assert not EvidenceSearchEmbedding.objects.exists()

    service = FakeService()
    monkeypatch.setattr(embeddings, "_call", service)
    with override_settings(EVIDENCE_EMBEDDINGS_URL="http://embeddings:80"):
        first = rebuild_search_index(actor="search-test", run_key="vectors")
        statements = first["summary"]["statements"]
        assert first["summary"]["embeddings"] == {
            "status": "succeeded",
            "model": embeddings.MODEL_KEY,
            "added": statements,
            "replaced": 0,
        }
        assert len(service.inputs) == statements
        assert all(text.startswith("passage: ") for text in service.inputs)
        again = rebuild_search_index(actor="search-test", run_key="vectors-again")
        assert again["summary"]["embeddings"]["added"] == 0

        # Another revision of the model recomputes every vector rather than mixing them.
        revision = "f" * 40
        monkeypatch.setattr(embeddings, "MODEL_REVISION", revision)
        monkeypatch.setattr(embeddings, "MODEL_KEY", f"{embeddings.MODEL}@{revision}")
        service.info["model_sha"] = revision
        changed = rebuild_search_index(actor="search-test", run_key="new-revision")
        assert changed["summary"]["embeddings"]["added"] == statements
        assert changed["summary"]["embeddings"]["replaced"] == statements
        assert set(EvidenceSearchEmbedding.objects.values_list("model", flat=True)) == {
            embeddings.MODEL_KEY
        }

        # A service serving an unexpected model leaves the full-text index intact.
        service.info["model_sha"] = "0" * 40
        refused = rebuild_search_index(actor="search-test", run_key="wrong-model")
        assert refused["status"] == "succeeded"
        assert refused["summary"]["embeddings"] == {"status": "unexpected_model"}
    assert EvidenceSearchEmbedding.objects.count() == statements


def test_semantic_and_hybrid_answers_cite_the_same_evidence(monkeypatch):
    ingest_baccarat()
    monkeypatch.setattr(embeddings, "_call", FakeService())
    with override_settings(EVIDENCE_EMBEDDINGS_URL="http://embeddings:80"):
        rebuild_search_index(actor="search-test", run_key="vectors")
    lexical = search_claims("penthouse")

    semantic = semantic_claims("penthouse")
    assert semantic[0]["kind"] == "typologies"
    assert semantic[0]["score"] > semantic[-1]["score"]
    assert {key: value for key, value in semantic[0].items() if key != "score"} == lexical[0]
    assert semantic_claims("penthouse", territory="al-reem-island") == []
    assert len(semantic_claims("penthouse", limit=2)) == 2
    assert semantic_claims("   ") == []

    # Semantic answers rank every statement, so the fusion holds them all.
    fused, answered = hybrid_claims("penthouse")
    assert answered and fused[0] == lexical[0]
    assert len(fused) == EvidenceSearchEntry.objects.count() > len(lexical)

    def unavailable(path, payload=None):
        raise embeddings.EmbeddingsUnavailable("unreachable")

    monkeypatch.setattr(embeddings, "_call", unavailable)
    assert hybrid_claims("penthouse") == (lexical, False)


def test_the_preview_route_fuses_the_semantic_ranking_on_request(client, monkeypatch):
    ingest_baccarat()
    monkeypatch.setattr(embeddings, "_call", FakeService())
    with override_settings(EVIDENCE_EMBEDDINGS_URL="http://embeddings:80"):
        rebuild_search_index(actor="search-test", run_key="vectors")
        with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
            text = client.get("/api/v1/preview/evidence-search", {"q": "penthouse"}).json()
            fused = client.get(
                "/api/v1/preview/evidence-search", {"q": "penthouse", "mode": "hybrid", "limit": 5}
            ).json()
        expected, _ = hybrid_claims("penthouse", limit=5)
    assert text["mode"] == "text" and text["semantic"] is False
    assert fused["mode"] == "hybrid" and fused["semantic"] is True
    assert [item["claim_key"] for item in fused["items"]] == [
        item["claim_key"] for item in expected
    ]
    assert all("score" not in item for item in fused["items"])


def test_the_evaluation_ranks_like_the_index_without_reading_or_writing_it(monkeypatch):
    ingest_baccarat()
    monkeypatch.setattr(embeddings, "_call", FakeService())
    with override_settings(EVIDENCE_EMBEDDINGS_URL="http://embeddings:80"):
        result = evaluate(k=5)
        assert EvidenceSearchEntry.objects.count() == 0
        rebuild_search_index(actor="search-test", run_key="vectors")
        fused, _ = hybrid_claims("penthouse", limit=50)
    lexical = search_claims("penthouse", limit=50)
    assert result["semantic"] is True
    assert result["statements"] == EvidenceSearchEntry.objects.count()
    rows = {(row["query"], row["mode"]): row for row in result["cases"]}
    assert len(rows) == len(CASES) * 3
    text, hybrid = rows["penthouse", "text"], rows["penthouse", "hybrid"]
    assert text["answered"] == len(lexical) and text["first_relevant_rank"] == 1
    assert hybrid["answered"] == len(fused)
    assert text["relevant"] == hybrid["relevant"] > 0
    assert 0 < text["relevant_in_top_5"] <= 5
    # A query in another language finds nothing in English texts without vectors.
    assert rows["piscine", "text"]["answered"] == 0

    with override_settings(EVIDENCE_EMBEDDINGS_URL=""):
        plain = evaluate(modes=("text", "hybrid"))
    assert plain["semantic"] is False
    assert {row["mode"] for row in plain["cases"]} == {"text"}
