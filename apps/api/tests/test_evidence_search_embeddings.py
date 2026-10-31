"""Client of the optional embeddings service, without the service (E01)."""

import io
import json
import math
from array import array

import pytest
from django.test import override_settings
from embeddings_fake import FakeService, vector

from property_platform.modules.evidence.search import embeddings


def test_texts_are_embedded_in_batches_with_their_retrieval_prefix(monkeypatch):
    service = FakeService()
    monkeypatch.setattr(embeddings, "_call", service)
    texts = [f"statement {index}" for index in range(70)]
    result = embeddings.embed(texts, role="passage")
    assert len(result) == 70 and all(len(item) == embeddings.DIMENSIONS * 4 for item in result)
    assert service.inputs == [f"passage: {text}" for text in texts]
    [query] = embeddings.embed(["statement 3"], role="query")
    assert service.inputs[-1] == "query: statement 3"
    assert math.isclose(embeddings.similarity(query, result[3]), 1.0, rel_tol=1e-6)
    # A database hands vectors back as memoryviews.
    assert math.isclose(
        embeddings.similarity(memoryview(query), memoryview(result[3])), 1.0, rel_tol=1e-6
    )
    assert array("f", result[3]).tolist() == pytest.approx(vector("statement 3"))


def test_a_service_serving_another_model_or_revision_is_refused(monkeypatch):
    monkeypatch.setattr(embeddings, "_call", FakeService(revision="0" * 40))
    with pytest.raises(embeddings.EmbeddingsUnavailable, match="unexpected_model"):
        embeddings.check_model()
    monkeypatch.setattr(embeddings, "_call", FakeService(model="other/model"))
    with pytest.raises(embeddings.EmbeddingsUnavailable, match="unexpected_model"):
        embeddings.check_model()
    monkeypatch.setattr(embeddings, "_call", FakeService())
    embeddings.check_model()


def test_vectors_of_the_wrong_size_are_refused(monkeypatch):
    monkeypatch.setattr(embeddings, "_call", lambda path, payload=None: [[1.0, 0.0]])
    with pytest.raises(embeddings.EmbeddingsUnavailable, match="unexpected_vectors"):
        embeddings.embed(["text"], role="query")


def test_without_a_configured_or_reachable_service_nothing_is_called(monkeypatch):
    with override_settings(EVIDENCE_EMBEDDINGS_URL=""):
        assert not embeddings.configured()
        with pytest.raises(embeddings.EmbeddingsUnavailable, match="not_configured"):
            embeddings.check_model()

    def refused(request, timeout):
        raise ConnectionRefusedError

    monkeypatch.setattr(embeddings, "urlopen", refused)
    with override_settings(EVIDENCE_EMBEDDINGS_URL="http://embeddings:80"):
        assert embeddings.configured()
        with pytest.raises(embeddings.EmbeddingsUnavailable, match="unreachable"):
            embeddings.check_model()


def test_requests_go_to_the_configured_service(monkeypatch):
    seen = []

    def answer(request, timeout):
        seen.append((request.full_url, request.data and json.loads(request.data)))
        return io.BytesIO(json.dumps([vector("x")]).encode())

    monkeypatch.setattr(embeddings, "urlopen", answer)
    with override_settings(EVIDENCE_EMBEDDINGS_URL="http://embeddings:80/"):
        embeddings.embed(["x"], role="query")
    assert seen == [
        (
            "http://embeddings:80/embed",
            {"inputs": ["query: x"], "normalize": True, "truncate": True},
        )
    ]
