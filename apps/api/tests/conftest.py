import pytest

from property_platform.modules.evidence import source_rights


@pytest.fixture
def unrestricted_sources(monkeypatch):
    """Tests of import and read mechanics whose fixtures use a restricted site (A19).

    Every host then keeps the unreviewed default. Archived receipts of a restricted
    site still replay exactly; what its rights hide is in `test_source_rights*.py`.
    """
    monkeypatch.setattr(source_rights, "source_rights", lambda: ())
