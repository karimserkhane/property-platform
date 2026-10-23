"""Version-keyed caching and conditional GETs for preview reads.

A response is identified by its request path, this process and the PostgreSQL
snapshot taken *before* its data is read. `pg_current_snapshot()` holds the next
transaction id and the writers still in progress, so any commit that could change
what a read returns also changes the snapshot: a cached body or an ETag is never
served after a change, including a source exclusion. Code or settings changes
restart the process, which empties the store and changes every ETag.

A path answered before (or revalidated by the client) reads the snapshot first and
can answer without running its view. A new path runs its view and records the
snapshot just before its first data statement, so a request rejected by validation
still never reaches the database.
"""

import hashlib
import secrets
import threading
from collections import OrderedDict
from functools import wraps

from django.db import connection
from django.http import HttpResponse

from .preview import enabled

PROCESS = secrets.token_hex(8)
MAX_BYTES = 64 * 1024 * 1024
MAX_ENTRY_BYTES = 8 * 1024 * 1024
CACHE_CONTROL = "private, no-cache"
SNAPSHOT_SQL = "SELECT pg_current_snapshot()::text"


class ByteBudgetLRU:
    """Thread-safe least-recently-used store bounded by total body bytes."""

    def __init__(self, max_bytes):
        self.max_bytes = max_bytes
        self.size = 0
        self._entries = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            self._entries.move_to_end(key)
            return entry[0]

    def put(self, key, value, size):
        with self._lock:
            previous = self._entries.pop(key, None)
            if previous is not None:
                self.size -= previous[1]
            self._entries[key] = (value, size)
            self.size += size
            while self.size > self.max_bytes:
                _, (_, evicted) = self._entries.popitem(last=False)
                self.size -= evicted

    def clear(self):
        with self._lock:
            self._entries.clear()
            self.size = 0


# One entry per path: snapshots only move forward, so older versions are useless.
store = ByteBudgetLRU(MAX_BYTES)


def data_version():
    with connection.cursor() as cursor:
        cursor.execute(SNAPSHOT_SQL)
        return cursor.fetchone()[0]


class FirstReadSnapshot:
    """Execute wrapper recording the snapshot just before the first data statement.

    Session settings (`SET TRANSACTION`, `SET LOCAL`) and savepoints run first, so a
    repeatable-read transaction records exactly the snapshot its reads will use.
    """

    def __init__(self):
        self.version = None

    def __call__(self, execute, sql, params, many, context):
        if self.version is None and not sql.lstrip().upper().startswith(
            ("SET ", "SAVEPOINT ", "RELEASE ", "ROLLBACK")
        ):
            # The context cursor runs through this wrapper again: mark it in progress.
            self.version = ""
            cursor = context["cursor"]
            cursor.execute(SNAPSHOT_SQL)
            self.version = cursor.fetchone()[0]
        return execute(sql, params, many, context)


def _etag(path, version):
    identity = f"{PROCESS}|{version}|{path}"
    return f'W/"{hashlib.sha256(identity.encode()).hexdigest()[:32]}"'


def _matches(header, etag):
    return any(tag.strip() in {etag, "*"} for tag in header.split(",")) if header else False


def _validated(response, etag):
    response["ETag"] = etag
    response["Cache-Control"] = CACHE_CONTROL
    return response


def cached_read(run):
    """Ninja view decorator (`decorate_view`) for bounded, side-effect-free GET reads."""

    @wraps(run)
    def read(request, *args, **kwargs):
        if request.method != "GET" or not enabled() or connection.vendor != "postgresql":
            return run(request, *args, **kwargs)
        path = request.get_full_path()
        known = store.get(path)
        conditional = request.headers.get("If-None-Match")
        if known is not None or conditional:
            etag = _etag(path, data_version())
            if _matches(conditional, etag):
                return _validated(HttpResponse(status=304), etag)
            if known is not None and known[0] == etag:
                status, body, content_type = known[1]
                return _validated(
                    HttpResponse(body, status=status, content_type=content_type), etag
                )
            response = run(request, *args, **kwargs)
        else:
            snapshot = FirstReadSnapshot()
            with connection.execute_wrapper(snapshot):
                response = run(request, *args, **kwargs)
            if snapshot.version is None:
                return response
            etag = _etag(path, snapshot.version)
        # Errors, streamed bodies and reads without data are never cached or validated.
        if response.status_code not in {200, 204} or response.streaming:
            return response
        body = response.content
        if len(body) <= MAX_ENTRY_BYTES:
            store.put(
                path, (etag, (response.status_code, body, response["Content-Type"])), len(body)
            )
        return _validated(response, etag)

    return read
