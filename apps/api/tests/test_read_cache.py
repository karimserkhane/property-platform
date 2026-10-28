from property_platform.api.read_cache import (
    ACCESSED_SQL,
    FIRST_READ_SQL,
    ByteBudgetLRU,
    ReadProbe,
)


def test_store_evicts_least_recently_used_bodies_beyond_its_byte_budget():
    store = ByteBudgetLRU(max_bytes=10)
    store.put("a", "body-a", 4)
    store.put("b", "body-b", 4)
    assert store.get("a") == "body-a"  # "b" is now the least recently used
    store.put("c", "body-c", 4)
    assert store.get("b") is None
    assert (store.get("a"), store.get("c")) == ("body-a", "body-c")
    assert store.size == 8
    store.put("a", "newer-a", 2)
    assert (store.get("a"), store.size) == ("newer-a", 6)
    store.clear()
    assert (store.size, store.get("a")) == (0, None)


class Database:
    alias = "default"
    in_atomic_block = True  # The view opened its own transaction.

    def __init__(self, cursor):
        self.own = cursor

    def cursor(self):
        return self.own


class Cursor:
    """Answers the probe's own statements; the scans grow with each data statement."""

    def __init__(self):
        self.db = Database(self)
        self.statements = []
        self.scans = {"parcel": 0, "place": 0}

    def execute(self, sql):
        self.statements.append(sql)
        self.last = sql

    def fetchone(self):
        return ("2026-10-26",) if self.last == "SELECT now()" else ("100:105:101", 7)

    def fetchall(self):
        return [("real_estate", table, scans) for table, scans in self.scans.items()]

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_probe_records_the_snapshot_before_the_first_read_and_the_tables_it_scans():
    probe, cursor, executed = ReadProbe(), Cursor(), []

    def execute(sql, params, many, context):
        executed.append(sql)
        if sql.startswith("SELECT"):
            cursor.scans[sql.rsplit(" ", 1)[1]] += 1

    context = {"cursor": cursor}
    for sql in [
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY",
        "SET LOCAL statement_timeout = '2000ms'",
        "SELECT id FROM parcel",
        "SELECT id FROM place",
    ]:
        probe(execute, sql, None, False, context)
    assert (probe.version, probe.revision) == ("100:105:101", 7)
    assert probe.tables == {("real_estate", "parcel"), ("real_estate", "place")}
    assert probe.atomic is None
    assert cursor.statements[:3] == [FIRST_READ_SQL, "SELECT now()", ACCESSED_SQL]
    assert cursor.statements.count(FIRST_READ_SQL) == 1
    assert len(executed) == 4
