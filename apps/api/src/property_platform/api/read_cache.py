"""Version-keyed caching and conditional GETs for preview reads.

A response is identified by its request path, this process and the PostgreSQL
snapshot taken *before* its data is read. `pg_current_snapshot()` holds the next
transaction id and the writers still in progress, so any commit that could change
what a read returns also changes the snapshot: an ETag is never validated after a
change, including a source exclusion. Code or settings changes restart the
process, which empties the store and changes every ETag.

A stored body is kept for its *table family*: the tables its view actually read,
counted by `pg_stat_xact_user_tables` in the transactions of its reads. When
every one of them carries the row journal (`evidence.install_row_journals`), the
body stays valid while no commit writes to them, so a write to another family no
longer discards it. `evidence.row_revision` is append-only and its ids come from a
sequence without session cache, so a commit to the family either adds a row with a
larger id than the latest one visible, or comes from a transaction that was still
in progress when the entry was checked; the entry keeps both and checks them again
on each read. A read of any table without a journal falls back to the snapshot.

A path answered before can answer without running its view. A new path runs its
view and records the snapshot just before its first data statement, so a request
rejected by validation still never reaches the database.
"""

import hashlib
import secrets
import threading
from collections import OrderedDict
from dataclasses import dataclass, replace
from functools import wraps

from django.db import connection, transaction
from django.http import HttpResponse

from .preview import enabled

PROCESS = secrets.token_hex(8)
MAX_BYTES = 64 * 1024 * 1024
MAX_ENTRY_BYTES = 8 * 1024 * 1024
CACHE_CONTROL = "private, no-cache"
SNAPSHOT_SQL = "SELECT pg_current_snapshot()::text"
# Snapshot of the reads, and the latest revision any of them could see.
FIRST_READ_SQL = (
    "SELECT pg_current_snapshot()::text, coalesce(max(id), 0) FROM evidence.row_revision"
)
ACCESSED_SQL = (
    "SELECT schemaname, relname, seq_scan + coalesce(idx_scan, 0) FROM pg_stat_xact_user_tables"
)
JOURNALED_SQL = (
    "SELECT n.nspname, c.relname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid"
    " JOIN pg_namespace n ON n.oid = c.relnamespace"
    " WHERE t.tgname = 'journal_row' AND NOT t.tgisinternal"
)
# Latest revision per table, transactions in progress, and whether any of the given
# transactions committed a revision of these tables, all from one snapshot.
FAMILY_SQL = """
SELECT
    array(SELECT coalesce((SELECT max(r.id) FROM evidence.row_revision r
                           WHERE r.schema_name = f.schema_name AND r.table_name = f.table_name), 0)
          FROM unnest(%(schemas)s::text[], %(tables)s::text[]) WITH ORDINALITY
               AS f(schema_name, table_name, position)
          ORDER BY f.position),
    array(SELECT x::text FROM pg_snapshot_xip(pg_current_snapshot()) AS x),
    EXISTS(SELECT 1 FROM evidence.row_revision r
           JOIN unnest(%(schemas)s::text[], %(tables)s::text[]) AS f(schema_name, table_name)
             ON r.schema_name = f.schema_name AND r.table_name = f.table_name
           WHERE r.transaction_id = ANY(%(pending)s::text[]) OR r.id > %(after)s)
"""
# Read by PostGIS for projections; changed only by the extension itself.
STATIC_TABLES = frozenset({("public", "spatial_ref_sys")})


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

    def replace(self, key, expected, value):
        """Swap an entry's value in place unless another request replaced it."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry[0] is expected:
                self._entries[key] = (value, entry[1])

    def clear(self):
        with self._lock:
            self._entries.clear()
            self.size = 0


@dataclass(frozen=True)
class Family:
    """Journaled tables a body was read from, their latest revisions and pending writers."""

    tables: tuple
    revisions: tuple
    pending: tuple


@dataclass(frozen=True)
class Entry:
    etag: str
    response: tuple
    snapshot: str
    family: Family | None


# One entry per path: versions only move forward, so older ones are useless.
store = ByteBudgetLRU(MAX_BYTES)


def data_version():
    with connection.cursor() as cursor:
        cursor.execute(SNAPSHOT_SQL)
        return cursor.fetchone()[0]


def _accessed(cursor):
    cursor.execute(ACCESSED_SQL)
    return {(schema, table): scans for schema, table, scans in cursor.fetchall()}


class ReadProbe:
    """Execute wrapper recording the snapshot and the tables of a view's reads.

    Session settings (`SET TRANSACTION`, `SET LOCAL`) and savepoints run first, so a
    repeatable-read transaction records exactly the snapshot its reads will use.
    Scan counters only last for one transaction: a data statement outside any
    transaction opens one for the rest of the view (so a request rejected before
    its first data statement still never connects), and the statements of a
    transaction the view opened itself are counted one by one.
    """

    def __init__(self):
        self.version = None
        self.revision = None
        self.tables = set()
        self.atomic = None
        self._busy = False
        self._transaction = None
        self._base = {}

    def __call__(self, execute, sql, params, many, context):
        if self._busy or sql.lstrip().upper().startswith(
            ("SET ", "SAVEPOINT ", "RELEASE ", "ROLLBACK")
        ):
            return execute(sql, params, many, context)
        cursor = context["cursor"]
        # The context cursor runs through this wrapper again.
        self._busy = True
        try:
            if self.atomic is None and not cursor.db.in_atomic_block:
                self.atomic = transaction.atomic(using=cursor.db.alias)
                self.atomic.__enter__()
            if self.version is None:
                cursor.execute(FIRST_READ_SQL)
                self.version, self.revision = cursor.fetchone()
            if self.atomic is None or self._transaction is None:
                cursor.execute("SELECT now()")
                started = cursor.fetchone()[0]
                if started != self._transaction:
                    self._transaction, self._base = started, _accessed(cursor)
        finally:
            self._busy = False
        result = execute(sql, params, many, context)
        if self.atomic is None:
            self._busy = True
            try:
                # A separate cursor keeps the view's results unread.
                with cursor.db.cursor() as own:
                    self.count(own)
            finally:
                self._busy = False
        return result

    def count(self, cursor):
        """Add the tables scanned in the current transaction since its baseline."""
        self.tables |= {
            key for key, scans in _accessed(cursor).items() if scans > self._base.get(key, 0)
        }

    def close(self, *exc_info):
        if self.atomic is not None:
            self.atomic.__exit__(*exc_info)


def _family_state(cursor, tables, pending, after):
    cursor.execute(
        FAMILY_SQL,
        {
            "schemas": [schema for schema, _ in tables],
            "tables": [table for _, table in tables],
            "pending": list(pending),
            "after": after,
        },
    )
    revisions, in_progress, committed = cursor.fetchone()
    return tuple(revisions), tuple(in_progress), committed


def _read_family(cursor, probe):
    """Family of the tables the view read, or None when one is not journaled."""
    if probe.atomic is not None:
        probe.count(cursor)
    tables = tuple(sorted(probe.tables - STATIC_TABLES))
    cursor.execute(JOURNALED_SQL)
    if not tables or not set(tables) <= set(cursor.fetchall()):
        return None
    # A commit to these tables since the first read may be missing from the body.
    xip = probe.version.split(":")[2]
    pending_then = tuple(xip.split(",")) if xip else ()
    revisions, pending, committed = _family_state(cursor, tables, pending_then, probe.revision)
    if committed:
        return None
    return Family(tables, revisions, pending)


def _still_valid(entry):
    """The entry's ETag if no commit changed what it was read from, with its refreshed form."""
    if entry.family is None:
        return entry if data_version() == entry.snapshot else None
    family = entry.family
    with connection.cursor() as cursor:
        revisions, in_progress, committed = _family_state(
            cursor, family.tables, family.pending, max(family.revisions)
        )
    if committed or revisions != family.revisions:
        return None
    # A writer that finished without a revision of these tables never adds one.
    pending = tuple(xid for xid in family.pending if xid in set(in_progress))
    if pending == family.pending:
        return entry
    return replace(entry, family=replace(family, pending=pending))


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
        if known is not None:
            valid = _still_valid(known)
            if valid is not None:
                if valid is not known:
                    store.replace(path, known, valid)
                if _matches(conditional, known.etag):
                    return _validated(HttpResponse(status=304), known.etag)
                status, body, content_type = known.response
                return _validated(
                    HttpResponse(body, status=status, content_type=content_type), known.etag
                )
        elif conditional:
            # No stored entry: only an unchanged snapshot proves the client's copy.
            etag = _etag(path, data_version())
            if _matches(conditional, etag):
                return _validated(HttpResponse(status=304), etag)
        probe = ReadProbe()
        try:
            with connection.execute_wrapper(probe):
                response = run(request, *args, **kwargs)
            if not probe.version or response.status_code not in {200, 204} or response.streaming:
                # Errors, streamed bodies and reads without data are never cached or validated.
                probe.close(None, None, None)
                return response
            with connection.cursor() as cursor:
                family = _read_family(cursor, probe)
        except BaseException as error:
            probe.close(type(error), error, error.__traceback__)
            raise
        probe.close(None, None, None)
        etag = _etag(path, probe.version)
        body = response.content
        if len(body) <= MAX_ENTRY_BYTES:
            entry = Entry(
                etag,
                (response.status_code, body, response["Content-Type"]),
                probe.version if family is None else "",
                family,
            )
            store.put(path, entry, len(body))
        return _validated(response, etag)

    return read
