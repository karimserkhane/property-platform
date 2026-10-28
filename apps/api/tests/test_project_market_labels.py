"""Reviewed ADREC sales label registry; portable checks without a database."""

import copy

import pytest

from property_platform.modules.evidence.projects.project_protocol import (
    project_market_labels,
    validate_project_market_labels,
)

PROJECTS = {
    "mamsha-garden": {
        "slug": "mamsha-garden",
        "name": "Mamsha Garden",
        "territory_id": "saadiyat-island",
        "sources": [
            {"url": "https://example.com/mamsha-garden", "role": "project"},
            {
                "url": "https://adrec.gov.ae/api/feature/Profession/ProjectDetail?id=581",
                "role": "project",
                "parser": "adrec_project_v1",
                "registration_number": "20240000361689",
                "heading_aliases": ["Mamsha Gardens B"],
            },
        ],
    },
    "flow-25": {
        "slug": "flow-25",
        "name": "Flow 25",
        "territory_id": "al-reem-island",
        "sources": [{"url": "https://example.com/flow-25", "role": "project"}],
    },
}


def label(**changes):
    return {
        "project": "flow-25",
        "district": "Al Reem Island",
        "label": "Flow25",
        "evidence": "project_name",
        "basis": "The ADREC sales label equals the registered project name.",
        "reviewed_on": "2026-10-26",
    } | changes


REGISTER = {
    "project": "mamsha-garden",
    "district": "Al Saadiyat Island",
    "label": "Mamsha Gardens B",
    "evidence": "register_name",
    "registration_number": "20240000361689",
}


def test_the_reviewed_registry_loads_and_scopes_by_territory():
    rows = project_market_labels()
    assert rows and len({(row["district"], row["label"]) for row in rows}) == len(rows)
    reem = project_market_labels("al-reem-island")
    assert reem and all(row["district"] == "Al Reem Island" for row in reem)


def test_a_label_may_equal_the_project_or_a_registration_name():
    validate_project_market_labels([label(), label(**REGISTER)], copy.deepcopy(PROJECTS))


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([label(project="missing")], "registered project"),
        ([label(district="Al Saadiyat Island")], "district"),
        ([label(label=" Flow25")], "exact ADREC"),
        ([label(label="Flow 26")], "cited registered name"),
        ([label(label="Flow")], "cited registered name"),
        ([label(evidence="similar_name")], "Unknown"),
        ([label(registration_number="20240000361689")], "cited registered name"),
        ([label(**REGISTER | {"registration_number": "2018/1"})], "cited registered name"),
        ([label(**REGISTER | {"label": "Mamsha Garden"})], "cited registered name"),
        ([label(basis=" ")], "basis"),
        ([label(reviewed_on="26/10/2026")], "Invalid isoformat"),
        ([label(), label(basis="Twice.")], "at most one"),
    ],
)
def test_invalid_labels_are_refused(rows, message):
    with pytest.raises(ValueError, match=message):
        validate_project_market_labels(rows, copy.deepcopy(PROJECTS))
