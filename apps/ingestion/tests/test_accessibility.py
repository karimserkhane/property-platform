import hashlib
from unittest.mock import patch

import httpx
import pytest

from property_platform_ingestion.collectors import accessibility as routing
from property_platform_ingestion.collectors.http import AcquisitionError


def client_for(respond):
    factory = httpx.Client
    return patch.object(
        routing.httpx,
        "Client",
        side_effect=lambda **kw: factory(transport=httpx.MockTransport(respond), **kw),
    )


def test_extract_redirect_and_bytes_are_fixed_and_receipted(tmp_path, monkeypatch):
    monkeypatch.setenv("ROUTING_STORAGE_DIR", str(tmp_path))
    payload = b"header-OSMHeader" + b"pbf-fixture" * 5
    seen = []

    def respond(request):
        seen.append(str(request.url))
        if request.method == "HEAD":
            return httpx.Response(
                307,
                headers={
                    "Location": "https://download.geofabrik.de/asia/gcc-states-261019.osm.pbf"
                },
            )
        return httpx.Response(
            200, content=payload, headers={"Content-Length": str(len(payload)), "ETag": "version-1"}
        )

    with client_for(respond):
        receipt = routing.acquire_graph()
    assert len(seen) == 2 and receipt.sha256 == hashlib.sha256(payload).hexdigest()
    assert b"".join(receipt.chunks()) == payload and receipt.etag == "version-1"
    assert receipt.fetched_at >= receipt.fetched_started_at


def test_no_arbitrary_redirect_or_oversized_source(tmp_path, monkeypatch):
    monkeypatch.setenv("ROUTING_STORAGE_DIR", str(tmp_path))
    with client_for(
        lambda _: httpx.Response(307, headers={"Location": "https://example.com/source"})
    ):
        with pytest.raises(AcquisitionError, match="Unregistered"):
            routing.acquire_graph()

    def respond(request):
        return (
            httpx.Response(200)
            if request.method == "HEAD"
            else httpx.Response(200, headers={"Content-Length": str(routing.MAX_GRAPH_BYTES + 1)})
        )

    with client_for(respond):
        with pytest.raises(AcquisitionError, match="budget"):
            routing.acquire_graph()
    assert list((tmp_path / "sources").iterdir()) == []


def test_db_replay_is_streamed_hash_checked_and_needs_no_source_network(tmp_path, monkeypatch):
    monkeypatch.setenv("ROUTING_STORAGE_DIR", str(tmp_path))
    payload = b"archived-pbf"
    sha = hashlib.sha256(payload).hexdigest()
    calls = []

    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={"active": sha, "building": None})

    with client_for(respond):
        routing.build_graph(sha, parts=iter([payload[:2], payload[2:]]))
    assert calls == ["http://routing:8003/status"]
    assert (tmp_path / "sources" / f"{sha}.osm.pbf").read_bytes() == payload
    with pytest.raises(ValueError, match="HashMismatch"):
        routing.build_graph(sha, parts=iter([b"corrupted"]))
    assert (tmp_path / "sources" / f"{sha}.osm.pbf").read_bytes() == payload


def test_engine_origin_cannot_become_external(monkeypatch):
    monkeypatch.setenv("ROUTING_ORIGIN", "https://example.com")
    with pytest.raises(ValueError, match="Unregistered"):
        routing.engine_client()
