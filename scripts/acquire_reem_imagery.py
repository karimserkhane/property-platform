"""Isolated acquisition worker; requires rasterio==1.5.2, never the API environment.

Produces a bounded acquisition receipt for import_reem_imagery. No HTML data is used.
"""

import argparse
import base64
import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

import rasterio
from rasterio.enums import Resampling
from rasterio.io import MemoryFile
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

BBOX = [54.3887, 24.4708, 54.4271, 24.5175]
SCENES = ["S2C_40RBN_20261004_0_L2A", "S2C_40RBN_20260629_0_L2A"]
BASE = "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/"


class RangeReader(io.RawIOBase):
    """Verified HTTPS range transport using Python's trust store on Windows."""

    def __init__(self, url):
        self.url, self.position, self.transferred = url, 0, 0
        with urlopen(Request(url, method="HEAD"), timeout=45) as r:
            self.length = int(r.headers["Content-Length"])

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset + (
            self.position if whence == 1 else self.length if whence == 2 else 0
        )
        return self.position

    def read(self, size=-1):
        size = min(self.length - self.position, size if size >= 0 else self.length)
        if size <= 0:
            return b""
        if size > 8 * 1024 * 1024 or self.transferred + size > 64 * 1024 * 1024:
            raise ValueError("Raster range budget exceeded")
        start = self.position
        with urlopen(
            Request(self.url, headers={"Range": f"bytes={start}-{start + size - 1}"}),
            timeout=45,
        ) as r:
            if r.status != 206:
                raise ValueError("Provider must support bounded byte ranges")
            value = r.read(size + 1)
        if len(value) != size:
            raise ValueError("Incomplete raster range")
        self.position += size
        self.transferred += size
        return value

    def readinto(self, buffer):
        value = self.read(len(buffer))
        buffer[: len(value)] = value
        return len(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = []
    for identity in SCENES:
        started = datetime.now(UTC).isoformat()
        with urlopen(
            Request(BASE + identity, headers={"User-Agent": "PropertyPlatform/0.1"}),
            timeout=45,
        ) as r:
            payload = r.read(1024 * 1024 + 1)
        if len(payload) > 1024 * 1024:
            raise ValueError("STAC capture too large")
        item = json.loads(payload)
        asset = item["assets"]["visual"]["href"]
        if not asset.startswith("https://sentinel-cogs.s3.us-west-2.amazonaws.com/"):
            raise ValueError("Unexpected raster host")

        # Read COG byte ranges, not the entire satellite tile. Render outside the API.
        def opener(path, mode="rb", *, asset_url=asset):
            if path != "scene.tif":
                raise FileNotFoundError(path)
            return RangeReader(asset_url)

        with (
            rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"),
            rasterio.open("scene.tif", opener=opener) as src,
            WarpedVRT(src, crs="EPSG:3857") as vrt,
        ):
            bounds = transform_bounds("EPSG:4326", "EPSG:3857", *BBOX)
            window = from_bounds(*bounds, transform=vrt.transform)
            width = min(768, round(window.width))
            height = min(768, round(window.height))
            rgb = vrt.read(
                indexes=[1, 2, 3],
                window=window,
                out_shape=(3, height, width),
                resampling=Resampling.bilinear,
            )
        with MemoryFile() as memory:
            with memory.open(
                driver="PNG", width=width, height=height, count=3, dtype="uint8"
            ) as image:
                image.write(rgb)
            preview = memory.read()
        results.append(
            {
                "url": BASE + identity,
                "payload": base64.b64encode(payload).decode(),
                "preview": base64.b64encode(preview).decode(),
                "preview_sha256": hashlib.sha256(preview).hexdigest(),
                "fetched_started_at": started,
                "fetched_at": datetime.now(UTC).isoformat(),
                "bbox": BBOX,
                "render_version": "reem-sentinel-crop-v1",
            }
        )
        print(f"{identity}: {width}x{height}, {len(preview)} bytes", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results), encoding="utf-8")


if __name__ == "__main__":
    main()
