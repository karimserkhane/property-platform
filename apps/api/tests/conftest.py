import pytest

from property_platform.modules.evidence import source_rights


@pytest.fixture
def unrestricted_sources(monkeypatch):
    """Tests of import and read mechanics whose fixtures use a restricted site (A19).

    Every host then keeps the unreviewed default. Archived receipts of a restricted
    site still replay exactly; what its rights hide is in `test_source_rights*.py`.
    """
    monkeypatch.setattr(source_rights, "source_rights", lambda: ())


@pytest.fixture
def enforce_rights(monkeypatch):
    """Switch each right on or off for a test, whatever the owner decided (A22)."""

    def enforce(*, collection=True, publication=True):
        switches = {"collection": collection, "publication": publication}
        decisions = {
            right: {
                "enforced": switches[right],
                "decided_on": "2026-10-27",
                "decided_by": "test",
                "basis": "Test switch.",
            }
            for right in source_rights.RIGHTS
        }
        monkeypatch.setattr(source_rights, "enforcement", lambda: decisions)

    return enforce


@pytest.fixture
def enforced_rights(enforce_rights):
    """Every right applied, as once the owner switches them on."""
    enforce_rights()
