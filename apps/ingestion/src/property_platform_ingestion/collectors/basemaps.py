"""Allowlisted, small-tile acquisition. No GIS/raster processing in the runner."""

import json
import re
from urllib.parse import urlencode

from .http import SourceHTTP


class BasemapCollector:
    def __init__(self, provider, coordinates=()):
        self.provider = provider
        self.template = None
        self.metadata = None
        self.coordinates = coordinates
        self.transport = SourceHTTP(
            ["https://tiles.openfreemap.org/planet/latest", "https://wmts.terrascope.be/wmts"],
            max_session_bytes=50 * 1024 * 1024,
            max_session_responses=102,
            total_timeout_seconds=300,
        )

    def __enter__(self):
        return self

    def _prepare(self):
        if self.provider == "openfreemap":
            if self.metadata is None:
                self.metadata = self.transport.fetch(
                    "https://tiles.openfreemap.org/planet/latest", max_bytes=1024 * 1024
                )
            if self.metadata.http_status != 200:
                raise ValueError("OpenFreeMap metadata is unavailable")
            value = json.loads(self.metadata.payload)
            templates = value.get("tiles", [])
            if len(templates) != 1 or not re.fullmatch(
                r"https://tiles\.openfreemap\.org/planet/[a-zA-Z0-9_./-]+/\{z\}/\{x\}/\{y\}\.pbf",
                templates[0],
            ):
                raise ValueError("Unreviewed vector tile origin or template")
            self.template = templates[0]
            self.transport.close()
            self.transport = SourceHTTP(
                [self.template.format(z=z, x=x, y=y) for z, x, y in self.coordinates]
                or ["https://tiles.openfreemap.org/planet/latest"],
                max_session_bytes=50 * 1024 * 1024,
                max_session_responses=101,
                total_timeout_seconds=300,
            )
        return self

    def __exit__(self, *args):
        self.transport.close()

    def __call__(self, request):
        if self.provider == "openfreemap":
            if self.template is None:
                self._prepare()
            url = self.template.format(z=request.z, x=request.x, y=request.y)
            return self.transport.fetch(url, max_bytes=4 * 1024 * 1024), self.template.split(
                "/planet/", 1
            )[1].split("/{z}", 1)[0]
        year = self.provider[-4:]
        if year not in {"2020", "2021"}:
            raise ValueError("Unregistered annual composite")
        version = "v1" if year == "2020" else "v2"
        params = {
            "SERVICE": "WMTS",
            "REQUEST": "GetTile",
            "VERSION": "1.0.0",
            "LAYER": f"esa-worldcover-s2rgbnir-10m-{year}-{version}_tcc",
            "STYLE": "",
            "TIME": f"{year}-01-01",
            "TILEMATRIXSET": "EPSG:3857",
            "TILEMATRIX": request.z,
            "TILECOL": request.x,
            "TILEROW": request.y,
            "FORMAT": "image/png",
        }
        return self.transport.fetch(
            "https://wmts.terrascope.be/wmts?" + urlencode(params),
            allowed_base="https://wmts.terrascope.be/wmts",
            max_bytes=1024 * 1024,
        ), f"{year}-{version}"
