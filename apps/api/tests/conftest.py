import pytest

from property_platform.modules.evidence import source_withdrawals


@pytest.fixture
def without_withdrawals(monkeypatch):
    """Tests of import and read mechanics whose fixtures use a withdrawn site (A19).

    Archived receipts of a withdrawn site still replay exactly; what the publication
    then hides is covered by `test_source_withdrawals*.py`.
    """
    monkeypatch.setattr(source_withdrawals, "withdrawals", lambda: ())
