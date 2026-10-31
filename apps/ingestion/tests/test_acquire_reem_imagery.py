"""The manual Sentinel-2 script follows the collection switch before each request (A27).

`scripts/acquire_reem_imagery.py` runs in its own Rasterio venv, outside both runtimes;
the ingestion image carries the same Rasterio and the API package, so it is tested here.
"""

import base64
import importlib.util
import json
from functools import cache
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

import numpy as np
import pytest
from property_platform.modules.evidence import source_fetch
from property_platform.modules.evidence.source_fetch import CollectionForbidden
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "acquire_reem_imagery.py"
STAC_HOST = "earth-search.aws.element84.com"
COG_HOST = "sentinel-cogs.s3.us-west-2.amazonaws.com"
COG = f"https://{COG_HOST}/sentinel-s2-l2a-cogs/40/R/BN/2026/10/S2C_40RBN_20261004_0_L2A/TCI.tif"


@pytest.fixture(scope="module")
def imagery():
    spec = importlib.util.spec_from_file_location("acquire_reem_imagery", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@cache
def raster():
    """Small true-colour COG over Reem, in WGS84 so the script's crop falls inside it."""
    with MemoryFile() as memory:
        with memory.open(
            driver="GTiff",
            width=120,
            height=140,
            count=3,
            dtype="uint8",
            crs="EPSG:4326",
            transform=from_origin(54.38, 24.53, 0.0005, 0.0005),
            tiled=True,
            blockxsize=16,
            blockysize=16,
        ) as dataset:
            dataset.write(np.full((3, 140, 120), 120, dtype=np.uint8))
        return memory.read()


class Response(BytesIO):
    def __init__(self, status, payload=b"", headers=None):
        super().__init__(payload)
        self.status, self.headers = status, headers or {}


def provider(opened, *, stac_status=200):
    """Earth Search items pointing at `COG`, and that COG's length and byte ranges."""

    def answer(request, timeout):
        opened.append((request.get_method(), request.full_url))
        if urlsplit(request.full_url).hostname == STAC_HOST:
            item = {"assets": {"visual": {"href": COG}}}
            return Response(stac_status, json.dumps(item).encode())
        payload = raster()
        if request.get_method() == "HEAD":
            return Response(200, headers={"Content-Length": str(len(payload))})
        start, end = (int(value) for value in request.get_header("Range")[6:].split("-"))
        return Response(206, payload[start : end + 1])

    return answer


# The map preview is a plain PNG, georeferenced by its receipt's bbox, not by GDAL.
@pytest.mark.filterwarnings("ignore::rasterio.errors.NotGeoreferencedWarning")
@pytest.mark.parametrize("enforced", [False, True])
@pytest.mark.parametrize("host", [STAC_HOST, COG_HOST])
def test_imagery_script_follows_the_collection_switch(
    imagery, host, enforced, enforce_collection, forbid_collection, tmp_path
):
    enforce_collection(enforced)
    forbid_collection(host)
    output = tmp_path / "sentinel-reem.json"
    opened = []
    with patch.object(source_fetch.OPENER, "open", side_effect=provider(opened)):
        if enforced:
            with pytest.raises(CollectionForbidden, match="forbid"):
                imagery.main(["--output", str(output)])
        else:
            imagery.main(["--output", str(output)])
    if enforced:
        # Refused before any request to the forbidden host, and before any receipt.
        assert all(urlsplit(url).hostname != host for _, url in opened)
        assert len(opened) == (0 if host == STAC_HOST else 1)
        assert not output.exists()
    else:
        receipt = json.loads(output.read_text("utf-8"))
        assert [row["url"] for row in receipt] == [imagery.BASE + i for i in imagery.SCENES]
        assert all(base64.b64decode(row["preview"]).startswith(b"\x89PNG") for row in receipt)
        assert {method for method, url in opened if url == COG} == {"HEAD", "GET"}


@pytest.mark.parametrize("enforced", [False, True])
def test_each_raster_request_follows_the_collection_switch(
    imagery, enforced, enforce_collection, forbid_collection
):
    """The switch is read before every request, so it also stops a run mid-raster."""
    enforce_collection(False)
    forbid_collection(COG_HOST)
    opened = []
    with patch.object(source_fetch.OPENER, "open", side_effect=provider(opened)):
        reader = imagery.RangeReader(COG)
        enforce_collection(enforced)
        if enforced:
            with pytest.raises(CollectionForbidden, match="forbid"):
                reader.read(16)
            with pytest.raises(CollectionForbidden, match="forbid"):
                imagery.RangeReader(COG)
        else:
            assert reader.read(16) == raster()[:16]
            assert imagery.RangeReader(COG).length == len(raster())
    assert [method for method, _ in opened] == (["HEAD"] if enforced else ["HEAD", "GET", "HEAD"])


def test_imagery_script_stops_on_an_http_error(imagery, enforce_collection, tmp_path):
    # `open_source` returns an error response for its capture; the script must not parse it.
    enforce_collection(False)
    with patch.object(source_fetch.OPENER, "open", side_effect=provider([], stac_status=404)):
        with pytest.raises(ValueError, match="HTTP 404"):
            imagery.main(["--output", str(tmp_path / "sentinel-reem.json")])
