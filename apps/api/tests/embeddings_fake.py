"""A stand-in for the local embeddings service: words hashed onto unit vectors."""

import hashlib
import math
import re

from property_platform.modules.evidence.search import embeddings


class FakeService:
    def __init__(self, model=embeddings.MODEL, revision=embeddings.MODEL_REVISION):
        self.info = {"model_id": model, "model_sha": revision}
        self.inputs = []

    def __call__(self, path, payload=None):
        if path == "/info":
            return self.info
        assert path == "/embed" and payload["normalize"] and payload["truncate"]
        assert len(payload["inputs"]) <= embeddings.BATCH
        self.inputs.extend(payload["inputs"])
        return [vector(text) for text in payload["inputs"]]


def vector(text):
    values = [0.0] * embeddings.DIMENSIONS
    for word in re.findall(r"\w+", text.lower()):
        if word in {"passage", "query"}:
            continue
        digest = hashlib.sha256(word.encode()).digest()
        values[int.from_bytes(digest[:4], "big") % embeddings.DIMENSIONS] += 1.0
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]
