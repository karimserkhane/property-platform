"""Local computation only. Prefect supplies archived OSM inputs; no external downloads."""

import hashlib
import json
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path("/routing")
LOCK = threading.Lock()
STATE = {"active": None, "building": None, "error": ""}
PROCESS = None


def launch(sha):
    global PROCESS
    config = ROOT / "graphs" / sha / "valhalla.json"
    if PROCESS is not None:
        PROCESS.terminate()
        try:
            PROCESS.wait(timeout=15)
        except subprocess.TimeoutExpired:
            PROCESS.kill()
    with (ROOT / "service.log").open("a") as output:
        PROCESS = subprocess.Popen(
            ["valhalla_service", str(config), "1"],
            stdout=output,
            stderr=subprocess.STDOUT,
        )
    for _ in range(60):
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:8002/status", timeout=2
            ) as response:
                if response.status == 200:
                    STATE["active"] = sha
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(1)
    raise RuntimeError("RouterStartupFailed")


def build(sha):
    with LOCK:
        old = STATE["active"]
        STATE.update(building=sha, error="")
        try:
            source = ROOT / "sources" / f"{sha}.osm.pbf"
            digest = hashlib.sha256()
            with source.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            if digest.hexdigest() != sha:
                raise ValueError("GraphInputHashMismatch")
            folder = ROOT / "graphs" / sha
            folder.mkdir(parents=True, exist_ok=True)
            config_path = folder / "valhalla.json"
            config = json.loads(
                subprocess.check_output(
                    [
                        "valhalla_build_config",
                        "--mjolnir-tile-dir",
                        str(folder / "tiles"),
                        "--mjolnir-concurrency",
                        "2",
                    ]
                )
            )
            config["httpd"]["service"]["listen"] = "tcp://127.0.0.1:8002"
            config["mjolnir"]["tile_extract"] = ""
            config["service_limits"]["pedestrian"]["max_distance"] = 50000
            config_path.write_text(json.dumps(config))
            if not (folder / "ready").exists():
                with (folder / "build.log").open("w") as log:
                    subprocess.run(
                        ["valhalla_build_tiles", "-c", str(config_path), str(source)],
                        check=True,
                        timeout=1800,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                (folder / "ready").write_text(sha)
            launch(sha)
            temporary = ROOT / "active.tmp"
            temporary.write_text(sha)
            temporary.replace(ROOT / "active")
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            STATE["error"] = type(exc).__name__
            if old:
                launch(old)
        finally:
            STATE["building"] = None


class Handler(BaseHTTPRequestHandler):
    def send(self, code, value):
        payload = json.dumps(value).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self.send(
            200 if self.path == "/status" else 404,
            STATE if self.path == "/status" else {"code": "not_found"},
        )

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", 0))
            if not 1 <= size <= 4096:
                raise ValueError("InvalidBody")
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise TypeError("InvalidBody")
            if self.path == "/build":
                sha = body.get("sha256", "")
                if (
                    set(body) != {"sha256"}
                    or not isinstance(sha, str)
                    or not re.fullmatch(r"[a-f0-9]{64}", sha)
                ):
                    raise ValueError("InvalidGraph")
                if STATE["building"]:
                    self.send(409, {"code": "busy"})
                    return
                STATE["building"] = sha
                threading.Thread(target=build, args=(sha,), daemon=True).start()
                self.send(202, {"code": "building"})
            elif self.path == "/isochrone":
                if (
                    set(body) != {"longitude", "latitude", "minutes", "graph"}
                    or body["graph"] != STATE["active"]
                ):
                    self.send(409, {"code": "graph_unavailable"})
                    return
                lon, lat, minutes = (
                    float(body["longitude"]),
                    float(body["latitude"]),
                    body["minutes"],
                )
                if not (51 <= lon <= 57 and 22 <= lat <= 27 and minutes in [5, 10, 15]):
                    raise ValueError("InvalidScope")
                payload = json.dumps(
                    {
                        "locations": [{"lon": lon, "lat": lat, "radius": 100}],
                        "costing": "pedestrian",
                        "contours": [{"time": minutes}],
                        "polygons": True,
                        "denoise": 0.1,
                        "generalize": 10,
                    }
                ).encode()
                request = urllib.request.Request(
                    "http://127.0.0.1:8002/isochrone",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=25) as response:
                    data = response.read(2 * 1024 * 1024 + 1)
                    if len(data) > 2 * 1024 * 1024:
                        raise ValueError("ResponseBudget")
                    self.send(200, json.loads(data))
            else:
                self.send(404, {"code": "not_found"})
        except (OSError, ValueError, TypeError, urllib.error.URLError):
            self.send(422, {"code": "calculation_failed"})


ROOT.mkdir(exist_ok=True, parents=True)
if (ROOT / "active").exists():
    saved = (ROOT / "active").read_text().strip()
    if re.fullmatch(r"[a-f0-9]{64}", saved):
        threading.Thread(target=build, args=(saved,), daemon=True).start()
ThreadingHTTPServer(("0.0.0.0", 8003), Handler).serve_forever()
