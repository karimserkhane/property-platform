from property_platform.api.read_cache import ByteBudgetLRU, FirstReadSnapshot


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


class Cursor:
    def __init__(self):
        self.statements = []

    def execute(self, sql):
        self.statements.append(sql)

    def fetchone(self):
        return ("100:105:101",)


def test_snapshot_is_recorded_after_session_settings_and_before_the_first_read():
    snapshot, cursor, executed = FirstReadSnapshot(), Cursor(), []

    def execute(sql, params, many, context):
        executed.append(sql)

    context = {"cursor": cursor}
    for sql in [
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY",
        "SET LOCAL statement_timeout = '2000ms'",
        "SELECT id FROM parcel",
        "SELECT id FROM place",
    ]:
        snapshot(execute, sql, None, False, context)
    assert snapshot.version == "100:105:101"
    assert cursor.statements == ["SELECT pg_current_snapshot()::text"]
    assert len(executed) == 4
