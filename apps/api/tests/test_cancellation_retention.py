"""Cancellation retention (B04): each band of the cited schedule, boundaries never guessed."""

from decimal import Decimal

import pytest

from property_platform.modules.publication.cancellation_retention import (
    PAID_SHARE_DISCRETION_PERCENT,
    SOURCE,
    VERSION,
    project_retention,
    retention,
)


@pytest.mark.parametrize(
    ("progress", "rate"),
    [
        (Decimal("0.01"), 10),
        (Decimal("9.99"), 10),
        (Decimal("10.01"), 15),
        (Decimal("29.99"), 15),
        (Decimal("30.01"), 25),
        (Decimal("59.99"), 25),
        (Decimal("60.01"), 40),
        (Decimal("96.5"), 40),
        (Decimal("100"), 40),
        (45, 25),
        (12.5, 15),
    ],
)
def test_a_progress_inside_a_band_reads_its_single_rate(progress, rate):
    result = retention(progress)

    assert result["status"] == "rate"
    assert result["rates"] == [rate]
    assert result["full_refund_possible"] is False
    assert result["progress_percent"] == progress


@pytest.mark.parametrize(
    ("progress", "rates"),
    [(Decimal("10"), [10, 15]), (Decimal("30.0"), [15, 25]), (60, [25, 40])],
)
def test_an_exact_boundary_returns_both_rates_because_the_source_is_silent(progress, rates):
    result = retention(progress)

    assert result["status"] == "boundary"
    assert result["rates"] == rates
    assert len(result["bands"]) == 2


def test_zero_progress_reads_the_first_band_and_flags_the_full_refund_case():
    result = retention(Decimal("0"))

    assert result["status"] == "rate"
    assert result["rates"] == [10]
    # Full refund depends on why works have not started, which ADREC assesses.
    assert result["full_refund_possible"] is True


@pytest.mark.parametrize("progress", [Decimal("-1"), Decimal("100.5"), Decimal("NaN")])
def test_an_impossible_progress_is_not_mapped(progress):
    result = retention(progress)

    assert result["status"] == "out_of_range"
    assert result["rates"] == []


def test_a_missing_progress_stays_unknown():
    result = retention(None)

    assert result["status"] == "unknown"
    assert result["rates"] == []


def test_every_reading_cites_its_dated_sources_and_the_paid_share_case():
    result = retention(Decimal("50"))

    assert result["version"] == VERSION
    assert result["paid_share_discretion_percent"] == PAID_SHARE_DISCRETION_PERCENT == 60
    assert result["source"] is SOURCE
    assert SOURCE["official_text_obtained"] is False
    for reference in SOURCE["references"]:
        assert reference["url"].startswith("https://")
        assert reference["published_on"] and reference["consulted_on"]


def test_project_retention_cites_the_declared_reading_of_an_off_plan_project():
    source = {"url": "https://adrec.gov.ae/project", "kind": "authority"}
    declared = {
        "progress_percent": Decimal("8.50"),
        "progress_inspected_on": "2026-06-29",
        "off_plan": True,
        "source": source,
    }
    result = project_retention(declared)
    assert result["rates"] == [10]
    assert result["progress_inspected_on"] == "2026-06-29"
    assert result["progress_source"] is source
    # Each commentary cites its site's reviewed rights; the shared schedule is untouched.
    for reference in result["source"]["references"]:
        assert reference["rights"]["licence"]
    assert all("rights" not in reference for reference in SOURCE["references"])


@pytest.mark.parametrize("off_plan", [False, None])
def test_project_retention_is_not_read_outside_off_plan_sales(off_plan):
    declared = {"progress_percent": 50, "progress_inspected_on": None, "off_plan": off_plan}
    assert project_retention(declared) is None
    assert project_retention(None) is None
