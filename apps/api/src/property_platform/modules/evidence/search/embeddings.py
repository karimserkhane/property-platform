"""Client of the optional local embeddings service (E01).

The model runs in its own Docker service (profile `embeddings`, Hugging Face Text
Embeddings Inference), never in the web/API runtime. Every vector records the pinned
model and revision it came from; a service serving another model is refused, so the
index never mixes vectors of different models. See docs/engineering/EVIDENCE_SEARCH.md.
"""

import json
from array import array
from urllib.request import Request, urlopen

from django.conf import settings

MODEL = "intfloat/multilingual-e5-small"
MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
MODEL_KEY = f"{MODEL}@{MODEL_REVISION}"
DIMENSIONS = 384
# The service accepts at most 32 inputs per request by default.
BATCH = 32
TIMEOUT = 60
# E5 models are trained with these prefixes on both sides of a retrieval.
PREFIXES = {"passage": "passage: ", "query": "query: "}


class EmbeddingsUnavailable(Exception):
    """The service is not configured, unreachable or serves another model."""


def configured():
    return bool(settings.EVIDENCE_EMBEDDINGS_URL)


def _call(path, payload=None):
    base = settings.EVIDENCE_EMBEDDINGS_URL.rstrip("/")
    if not base:
        raise EmbeddingsUnavailable("not_configured")
    body = None if payload is None else json.dumps(payload).encode()
    request = Request(f"{base}{path}", data=body, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read())
    except (OSError, ValueError) as exc:
        raise EmbeddingsUnavailable("unreachable") from exc


def check_model():
    """Refuse a service that does not serve the pinned model and revision."""
    info = _call("/info")
    if info.get("model_id") != MODEL or info.get("model_sha") != MODEL_REVISION:
        raise EmbeddingsUnavailable("unexpected_model")


def embed(texts, *, role):
    """Unit vectors of the texts, as float32 bytes, in order."""
    prefix = PREFIXES[role]
    result = []
    for start in range(0, len(texts), BATCH):
        batch = [prefix + text for text in texts[start : start + BATCH]]
        vectors = _call("/embed", {"inputs": batch, "normalize": True, "truncate": True})
        if len(vectors) != len(batch) or any(len(vector) != DIMENSIONS for vector in vectors):
            raise EmbeddingsUnavailable("unexpected_vectors")
        result.extend(array("f", vector).tobytes() for vector in vectors)
    return result


def similarity(left, right):
    """Cosine similarity of two unit vectors stored as float32 bytes."""
    # A database returns a memoryview, which array() would read as bytes, not floats.
    left, right = array("f", bytes(left)), array("f", bytes(right))
    return sum(a * b for a, b in zip(left, right, strict=True))
