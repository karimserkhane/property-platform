"""Reviewed verification page registry; portable checks without a database."""

import copy

import pytest

from property_platform.modules.evidence.projects.project_protocol import (
    project_verification_links,
    validate_project_verification_links,
)

PAGE = "https://www.dari.ae/en/app/directory/project/730"


def project(slug, *numbers):
    return {
        "slug": slug,
        "territory_id": "saadiyat-island",
        "sources": [
            {"url": f"https://example.com/{slug}", "role": "project"},
            *(
                {
                    "url": f"https://adrec.gov.ae/api/feature/Profession/ProjectDetail?id={index}",
                    "role": "project",
                    "parser": "adrec_project_v1",
                    "registration_number": number,
                }
                for index, number in enumerate(numbers, start=1)
            ),
        ],
    }


PROJECTS = {
    "registered": project("registered", "20260001482662", "2018/442116"),
    "unregistered": project("unregistered"),
}


def link(**changes):
    return {
        "project": "registered",
        "registration_number": "20260001482662",
        "url": PAGE,
        "basis": "Directory page opened by the operator shows this project number.",
        "reviewed_on": "2026-10-24",
    } | changes


def test_the_reviewed_registry_loads():
    # Empty until an operator records a page; it still validates against the registry.
    assert isinstance(project_verification_links(), tuple)
    assert isinstance(project_verification_links("saadiyat-island"), tuple)


def test_one_page_per_registration_of_a_project():
    rows = [
        link(),
        link(
            registration_number="2018/442116",
            url="https://www.dari.ae/en/app/directory/project/731",
        ),
    ]
    validate_project_verification_links(rows, copy.deepcopy(PROJECTS))


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([link(project="missing")], "registered project"),
        ([link(project="unregistered")], "registered ADREC registration"),
        ([link(registration_number="20260000000000")], "registered ADREC registration"),
        ([link(url="https://www.dari.ae/en/app/directory/project/730?x=1")], "DARI project"),
        ([link(url="https://api.dari.ae/property-service/api/v1/property/project")], "DARI"),
        ([link(url="http://www.dari.ae/en/app/directory/project/730")], "DARI project"),
        ([link(basis=" ")], "basis"),
        ([link(reviewed_on="24/10/2026")], "Invalid isoformat"),
        ([link(), link(url="https://www.dari.ae/en/app/directory/project/731")], "at most one"),
        ([link(), link(registration_number="2018/442116")], "one registration"),
    ],
)
def test_invalid_links_are_refused(rows, message):
    with pytest.raises(ValueError, match=message):
        validate_project_verification_links(rows, copy.deepcopy(PROJECTS))
