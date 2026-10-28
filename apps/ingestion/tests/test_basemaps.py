import json
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from property_platform_ingestion.collectors.basemaps import BasemapCollector
from property_platform_ingestion.collectors.http import SourceHTTP


def test_vector_acquisition_keeps_the_metadata_and_allows_only_its_fixed_origin():
    visited = []

    def respond(request):
        visited.append(str(request.url))
        if request.url.path.endswith("/latest"):
            return httpx.Response(
                200,
                stream=httpx.ByteStream(
                    json.dumps(
                        {
                            "tiles": [
                                "https://tiles.openfreemap.org/planet/20261011_080001_pt/{z}/{x}/{y}.pbf"
                            ]
                        }
                    ).encode()
                ),
            )
        return httpx.Response(200, stream=httpx.ByteStream(b"\x1a\x00"))

    def transport(urls, **kwargs):
        return SourceHTTP(
            urls, transport=httpx.MockTransport(respond), min_interval_seconds=0, **kwargs
        )

    with patch("property_platform_ingestion.collectors.basemaps.SourceHTTP", side_effect=transport):
        with BasemapCollector("openfreemap", [(13, 5334, 3520)]) as collector:
            tile, version = collector(SimpleNamespace(z=13, x=5334, y=3520))
            assert tile.payload == b"\x1a\x00" and version == "20261011_080001_pt"
            assert json.loads(collector.metadata.payload)["tiles"]
    assert len(visited) == 2


def test_changed_metadata_cannot_redirect_collection_to_an_arbitrary_host():
    def transport(urls, **kwargs):
        return SourceHTTP(
            urls,
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    stream=httpx.ByteStream(
                        json.dumps({"tiles": ["https://example.com/{z}/{x}/{y}.pbf"]}).encode()
                    ),
                )
            ),
            min_interval_seconds=0,
            **kwargs,
        )

    with patch("property_platform_ingestion.collectors.basemaps.SourceHTTP", side_effect=transport):
        with BasemapCollector("openfreemap", [(13, 5334, 3520)]) as collector:
            with pytest.raises(ValueError, match="Unreviewed"):
                collector(SimpleNamespace(z=13, x=5334, y=3520))
            assert collector.metadata.http_status == 200  # receipt remains available for audit
