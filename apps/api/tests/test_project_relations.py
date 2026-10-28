"""Reviewed project relation registry; portable checks without a database."""

import copy

import pytest

from property_platform.modules.evidence.projects.project_protocol import (
    project_relations,
    validate_project_relations,
)


def project(slug, territory="al-reem-island", url=None):
    return {
        "slug": slug,
        "territory_id": territory,
        "sources": [
            {"url": url or f"https://example.com/{slug}", "role": "project"},
            {"url": "https://example.com/terms", "role": "terms"},
        ],
    }


PROJECTS = {
    slug: project(slug) for slug in ("programme", "tower-1", "tower-2", "phase", "elsewhere")
} | {"saadiyat": project("saadiyat", territory="saadiyat-island")}


def relation(child, parent, **changes):
    return {
        "child": child,
        "parent": parent,
        "kind": "part_of",
        "component": "Tower 1",
        "source_url": f"https://example.com/{child}",
        "basis": "Named by the source.",
        "reviewed_on": "2026-10-23",
    } | changes


def test_the_reviewed_registry_is_valid_and_scoped_by_territory():
    rows = project_relations()
    assert {row["child"] for row in rows} >= {"gate", "the-arc", "mayar-in-maysan"}
    reem = project_relations("al-reem-island:gate")
    assert all(row["child"] != "the-row-saadiyat-phase-2" for row in reem)
    assert any(
        row["child"] == "the-row-saadiyat-phase-2" for row in project_relations("saadiyat-island")
    )


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([relation("tower-1", "missing")], "two registered projects"),
        ([relation("tower-1", "tower-1")], "two registered projects"),
        ([relation("tower-1", "saadiyat")], "one territory"),
        ([relation("tower-1", "programme", kind="same_as")], "Unknown project relation kind"),
        (
            [relation("tower-1", "programme", source_url="https://example.com/terms")],
            "registered project source",
        ),
        ([relation("tower-1", "programme", basis=" ")], "component, basis"),
        (
            [relation("tower-1", "programme"), relation("tower-1", "phase")],
            "at most one parent",
        ),
        (
            [
                relation("programme", "phase", source_url="https://example.com/programme"),
                relation("phase", "programme", source_url="https://example.com/phase"),
            ],
            "cycle",
        ),
    ],
)
def test_invalid_relations_are_refused(rows, message):
    with pytest.raises(ValueError, match=message):
        validate_project_relations(rows, copy.deepcopy(PROJECTS))


def test_a_parent_source_may_document_its_components():
    rows = [
        relation("tower-1", "programme", source_url="https://example.com/programme"),
        relation("tower-2", "programme", component="Tower 2"),
        relation("programme", "phase", source_url="https://example.com/phase"),
    ]
    validate_project_relations(rows, PROJECTS)
