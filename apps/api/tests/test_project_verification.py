"""Register verification facts are read as published, never completed or derived."""

from datetime import date
from decimal import Decimal

from property_platform.modules.evidence.projects.project_adrec import adrec_verification

POINTER = "JSON:Data.Result[Id=436,ProjectNumber=2022/128971]"


def record(**values):
    base = {
        "Id": 436,
        "ProjectNumber": "2022/128971",
        "Status": "Under Construction",
        "IsOffplan": True,
        "PermitNumber": "1003168",
        "ProjectCreateDate": "2022-03-18T00:00:00",
        "ProgressPercentage": 96.5,
        # 2026-08-20T20:00Z is 21 August in the UAE.
        "InspectionDate": "/Date(1787256000000)/",
        "SoldUnit": "98.57%",
        "EscrowBankName": "FIRST ABU DHABI BANK P.J.S.C.",
        "EscrowNumber": "4031221018122003",
        "EscrowIban": "AE000000000000000000000",
        "DeveloperTradeLicense": "CN-1003168",
        "LatestReport": {
            "InspectionDate": "2026-08-21",
            "CompletionPercentage": 96.5,
            "InspectionCompany": "ADCE",
            "ValidityDate": "2026-11-21",
            "Report": "https://example.blob.core.windows.net/report.pdf",
        },
    }
    base.update(values)
    return base


def test_register_facts_keep_their_own_dates_and_original_values():
    facts = adrec_verification(record(), {"fact_scope": "project"}, POINTER)
    assert facts == {
        "authority": "adrec",
        "record_id": "436",
        "fact_scope": "project",
        "registration_number": "2022/128971",
        "permit_number": "1003168",
        "register_status": "Under Construction",
        "off_plan": True,
        "registered_on": date(2022, 3, 18),
        "progress_percent": Decimal("96.50"),
        "progress_inspected_on": date(2026, 8, 21),
        "inspection_company": "ADCE",
        "progress_report_valid_until": date(2026, 11, 21),
        "progress_report_url": "https://example.blob.core.windows.net/report.pdf",
        "sold_percent": Decimal("98.57"),
        "sold_original": "98.57%",
        "escrow_bank_name": "FIRST ABU DHABI BANK P.J.S.C.",
        "escrow_account_number": "4031221018122003",
        "developer_licence": "CN-1003168",
        "evidence_pointer": POINTER,
    }
    assert "AE000000000000000000000" not in facts.values()  # The IBAN is not copied.


def test_bare_zero_sale_share_is_not_read_as_zero_percent_sold():
    facts = adrec_verification(record(SoldUnit="0"), {}, POINTER)
    assert facts["sold_percent"] is None
    assert facts["sold_original"] == "0"
    assert adrec_verification(record(SoldUnit="0%"), {}, POINTER)["sold_percent"] == 0


def test_report_that_disagrees_with_the_headline_progress_is_not_attached():
    report = {**record()["LatestReport"], "CompletionPercentage": 90}
    facts = adrec_verification(record(LatestReport=report), {}, POINTER)
    assert facts["progress_percent"] == Decimal("96.50")
    assert facts["progress_inspected_on"] == date(2026, 8, 21)
    assert facts["inspection_company"] == ""
    assert facts["progress_report_url"] == ""
    assert facts["progress_report_valid_until"] is None


def test_missing_or_malformed_values_stay_unknown():
    facts = adrec_verification(
        record(
            ProgressPercentage=True,
            InspectionDate="21/08/2026",
            IsOffplan="yes",
            PermitNumber=None,
            EscrowBankName=None,
            EscrowNumber=None,
            ProjectCreateDate=None,
            LatestReport=None,
            SoldUnit=None,
        ),
        {"fact_scope": "identity_only"},
        POINTER,
    )
    assert facts["fact_scope"] == "identity_only"
    for key in ("progress_percent", "progress_inspected_on", "off_plan", "registered_on"):
        assert facts[key] is None
    for key in ("permit_number", "escrow_bank_name", "escrow_account_number", "sold_original"):
        assert facts[key] == ""


def test_inspection_date_needs_a_progress_value():
    facts = adrec_verification(record(ProgressPercentage=None), {}, POINTER)
    assert facts["progress_percent"] is None
    assert facts["progress_inspected_on"] is None
    assert facts["inspection_company"] == ""
