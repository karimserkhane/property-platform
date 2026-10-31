import pytest
from property_platform.modules.evidence import source_rights


@pytest.fixture
def enforce_collection(monkeypatch):
    """Switch collection enforcement for a test, whatever the owner decided (A22)."""

    def enforce(enforced=True):
        decisions = {right: dict(value) for right, value in source_rights.enforcement().items()}
        decisions["collection"]["enforced"] = enforced
        monkeypatch.setattr(source_rights, "enforcement", lambda: decisions)

    return enforce


@pytest.fixture
def collection_enforced(enforce_collection):
    """Collectors follow each site's terms, as the refusal tests expect."""
    enforce_collection()


@pytest.fixture
def forbid_collection(monkeypatch):
    """Review hosts as forbidding collection, whatever their terms say today (A25)."""

    def forbid(*hosts):
        rows = tuple(
            {**row, "collection": "forbidden"} if row["host"] in hosts else row
            for row in source_rights.source_rights()
        )
        monkeypatch.setattr(source_rights, "source_rights", lambda: rows)

    return forbid
