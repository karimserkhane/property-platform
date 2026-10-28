"""Fixed OSM extract intake and bounded requests to the private computation engine."""

import hashlib
import os
import re
import ssl
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from .http import AcquisitionError

GRAPH_URL = "https://download.geofabrik.de/asia/gcc-states-latest.osm.pbf"
MAX_GRAPH_BYTES = 320 * 1024 * 1024


@dataclass(frozen=True)
class GraphReceipt:
    url: str
    path: Path
    byte_length: int
    sha256: str
    fetched_started_at: datetime
    fetched_at: datetime
    etag: str
    last_modified_raw: str
    http_status: int = 200

    def capture_receipt(self):
        return {
            "url": self.url,
            "fetched_started_at": self.fetched_started_at,
            "fetched_at": self.fetched_at,
            "http_status": self.http_status,
            "etag": self.etag,
            "last_modified_raw": self.last_modified_raw,
            "timestamp_basis": "collector_clock",
        }

    def chunks(self):
        with self.path.open("rb") as stream:
            while chunk := stream.read(4 * 1024 * 1024):
                yield chunk


def acquire_graph():
    root = Path(os.environ.get("ROUTING_STORAGE_DIR", "/routing")) / "sources"
    root.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC)
    deadline = time.monotonic() + 300
    digest, size = hashlib.sha256(), 0
    # This single reviewed regional extract has a separate byte budget. The
    # generic small-source transport and its 64 MiB session limit stay unchanged.
    with httpx.Client(
        verify=ssl.create_default_context(),
        follow_redirects=False,
        timeout=30,
        headers={
            "User-Agent": "PropertyPlatform/1.0 OSM-routing-intake",
            "Accept-Encoding": "identity",
        },
    ) as client:
        metadata = client.head(GRAPH_URL)
        url = GRAPH_URL
        if metadata.status_code in (301, 302, 303, 307, 308):
            url = metadata.headers.get("Location", "")
            if not re.fullmatch(
                r"https://download\.geofabrik\.de/asia/gcc-states-\d{6}\.osm\.pbf", url
            ):
                raise AcquisitionError("Unregistered regional extract redirect")
        elif metadata.status_code != 200:
            raise AcquisitionError("Regional extract metadata unavailable")
        with client.stream("GET", url) as response:
            if (
                response.status_code != 200
                or response.headers.get("Content-Encoding", "identity") != "identity"
            ):
                raise AcquisitionError("Regional routing extract unavailable")
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > MAX_GRAPH_BYTES:
                raise AcquisitionError("Routing source byte budget exceeded")
            with tempfile.NamedTemporaryFile(dir=root, delete=False, suffix=".partial") as output:
                partial = Path(output.name)
                try:
                    for chunk in response.iter_bytes(1024 * 1024):
                        size += len(chunk)
                        if size > MAX_GRAPH_BYTES or time.monotonic() > deadline:
                            raise AcquisitionError("Routing source acquisition budget exceeded")
                        digest.update(chunk)
                        output.write(chunk)
                except BaseException:
                    output.close()
                    partial.unlink(missing_ok=True)
                    raise
            completed = datetime.now(UTC)
            sha = digest.hexdigest()
            path = root / f"{sha}.osm.pbf"
            partial.replace(path)
            with path.open("rb") as stream:
                header = stream.read(100)
            if not size or b"OSMHeader" not in header or (declared and int(declared) != size):
                raise AcquisitionError("Invalid or truncated OSM PBF")
            return GraphReceipt(
                url=url,
                path=path,
                byte_length=size,
                sha256=sha,
                fetched_started_at=started,
                fetched_at=completed,
                http_status=200,
                etag=response.headers.get("ETag", "")[:500],
                last_modified_raw=response.headers.get("Last-Modified", "")[:160],
            )


def engine_client():
    origin = os.environ.get("ROUTING_ORIGIN", "http://routing:8003")
    if origin != "http://routing:8003":
        raise ValueError("Unregistered routing engine origin")
    return httpx.Client(base_url=origin, timeout=30, follow_redirects=False, trust_env=False)


def build_graph(sha, *, parts=None):
    if parts is not None:
        root = Path(os.environ.get("ROUTING_STORAGE_DIR", "/routing")) / "sources"
        root.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        with tempfile.NamedTemporaryFile(dir=root, delete=False, suffix=".restore") as output:
            temporary = Path(output.name)
            try:
                for chunk in parts:
                    if len(chunk) > 4 * 1024 * 1024:
                        raise ValueError("RestoredGraphChunkBudget")
                    digest.update(chunk)
                    output.write(chunk)
            except BaseException:
                output.close()
                temporary.unlink(missing_ok=True)
                raise
        if digest.hexdigest() != sha:
            temporary.unlink(missing_ok=True)
            raise ValueError("RestoredGraphHashMismatch")
        temporary.replace(root / f"{sha}.osm.pbf")
    with engine_client() as client:
        status = client.get("/status").json()
        if status.get("active") == sha and not status.get("building"):
            return
        response = client.post("/build", json={"sha256": sha})
        if response.status_code not in (202, 409):
            raise ValueError("GraphBuildRejected")
        deadline = time.monotonic() + 780
        while time.monotonic() < deadline:
            state = client.get("/status").json()
            if state.get("active") == sha and not state.get("building"):
                return
            if state.get("error") and not state.get("building"):
                raise ValueError("GraphBuildFailed")
            time.sleep(5)
    raise ValueError("GraphBuildDeadline")


def compute_walking(request, graph_sha):
    with engine_client() as client:
        response = client.post(
            "/isochrone",
            json={
                "longitude": str(request.longitude),
                "latitude": str(request.latitude),
                "minutes": request.minutes,
                "graph": graph_sha,
            },
        )
        if response.status_code != 200 or len(response.content) > 2 * 1024 * 1024:
            raise ValueError("WalkingCalculationFailed")
        return response.json()
