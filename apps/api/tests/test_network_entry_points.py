"""Every direct network call in the repository goes through a controlled entry point (A25).

A source site is read only through `SourceHTTP` or the collectors and connectors that
check the collection switch before each request; other clients reach a private service.
A new `httpx`, `urlopen`, `requests` (or similar) call anywhere else fails here: route
it through an entry point below, or add it with the reason it is controlled.
"""

import ast
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCANNED = ("apps", "infra", "scripts")
SKIPPED = {"tests", "node_modules", ".venv", "__pycache__", ".next"}
NETWORK = {
    *(f"httpx.{name}" for name in ("Client", "AsyncClient", "request", "stream")),
    *(f"httpx.{verb}" for verb in ("get", "head", "post", "put", "patch", "delete", "options")),
    *(f"urllib.request.{name}" for name in ("urlopen", "urlretrieve", "build_opener")),
    "urllib.request.OpenerDirector",
    "http.client.HTTPConnection",
    "http.client.HTTPSConnection",
    "socket.create_connection",
    "socket.socket",
}
NETWORK_PACKAGES = ("requests", "urllib3", "aiohttp")

API = "apps/api/src/property_platform/modules/evidence/"
COLLECTORS = "apps/ingestion/src/property_platform_ingestion/collectors/"
SOURCE_SITE = "Source site, collection switch checked before each request"
ENTRY_POINTS = {
    (API + "source_fetch.py", "<module>"): SOURCE_SITE + " and redirect (A25)",
    (COLLECTORS + "http.py", "SourceHTTP.__init__"): SOURCE_SITE + " (SourceHTTP.fetch)",
    (COLLECTORS + "sentinel_windows.py", "RangeSession.__init__"): SOURCE_SITE,
    (COLLECTORS + "accessibility.py", "acquire_graph"): SOURCE_SITE + " and redirect",
    (COLLECTORS + "accessibility.py", "engine_client"): "Private routing engine, fixed origin",
    (API + "search/embeddings.py", "_call"): "Private embeddings service (E01)",
    ("infra/local/routing/server.py", "launch"): "Valhalla on 127.0.0.1",
    ("infra/local/routing/server.py", "Handler.do_POST"): "Valhalla on 127.0.0.1",
}


def imported_names(tree):
    names = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                names[local] = alias.name if alias.asname else local
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                names[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return names


def dotted(node, names):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name) and node.id in names:
        return ".".join([names[node.id], *reversed(parts)])
    return None


def is_network(name):
    return name in NETWORK or name.split(".")[0] in NETWORK_PACKAGES


class NetworkUses(ast.NodeVisitor):
    """Scopes (`Class.method`, `function` or `<module>`) that reference a network client."""

    def __init__(self, names):
        self.names, self.scope, self.found = names, [], set()

    def visit_scope(self, node):
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = visit_scope

    def visit_reference(self, node):
        name = dotted(node, self.names)
        if name is not None and is_network(name):
            self.found.add(".".join(self.scope) or "<module>")
        else:
            self.generic_visit(node)

    visit_Name = visit_Attribute = visit_reference


def network_uses():
    found = set()
    for base in SCANNED:
        for directory, subdirectories, files in os.walk(ROOT / base):
            subdirectories[:] = sorted(set(subdirectories) - SKIPPED)
            for file in sorted(name for name in files if name.endswith(".py")):
                path = Path(directory) / file
                tree = ast.parse(path.read_text("utf-8"), filename=str(path))
                uses = NetworkUses(imported_names(tree))
                uses.visit(tree)
                relative = path.relative_to(ROOT).as_posix()
                found |= {(relative, scope) for scope in uses.found}
    return found


def test_direct_network_calls_stay_in_controlled_entry_points():
    found = network_uses()
    assert found - set(ENTRY_POINTS) == set(), "Direct network call outside an entry point"
    assert set(ENTRY_POINTS) - found == set(), "Entry point no longer found: update the list"


def test_the_scan_finds_each_kind_of_direct_call():
    source = """
import httpx, requests
import urllib.request as web
from urllib.request import urlopen as fetch
from http.client import HTTPSConnection

def a():
    return httpx.get("https://example.com")

def b():
    return requests.Session()

def c():
    return web.urlopen("https://example.com")

class D:
    def e(self):
        return fetch

opener = web.build_opener()
connection = HTTPSConnection("example.com")
"""
    tree = ast.parse(source)
    uses = NetworkUses(imported_names(tree))
    uses.visit(tree)
    assert uses.found == {"a", "b", "c", "D.e", "<module>"}
