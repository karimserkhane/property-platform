"""Synthetic publisher contracts: discovery is a review queue, not geospatial identity."""

import copy
import json

import pytest
from property_platform.modules.evidence.project_discovery import (
    candidates_for,
    catalogue_for,
)
from property_platform.modules.evidence.project_protocol import (
    extract_project_source,
    project_registry,
)


def aldar_catalogue(items=None, total=1):
    return json.dumps(
        {
            "data": {
                "total": total,
                "communities": items
                if items is not None
                else [{"communityId": "a228d000000XzsQAAS", "projectName": "A new project"}],
            }
        }
    ).encode()


def test_catalogue_scope_is_closed_and_a_full_page_is_required():
    definition = catalogue_for("saadiyat-island:aldar-saadiyat")
    candidates = candidates_for(definition, aldar_catalogue())
    assert candidates[0]["title"] == "A new project"
    assert candidates[0]["source_url"].endswith("/a228d000000XzsQAAS")
    for payload in [aldar_catalogue(total=101), aldar_catalogue(items=[]), b"{}"]:
        with pytest.raises(ValueError):
            candidates_for(definition, payload)
    for scope in [
        "dubai:aldar-saadiyat",
        "al-reem-island:aldar-saadiyat",
        "saadiyat-island:https://example.com",
    ]:
        with pytest.raises(ValueError):
            catalogue_for(scope)


def test_html_catalogues_keep_only_registered_publisher_project_paths():
    definition = catalogue_for("al-reem-island:saas-reem")
    payload = b"""<html><a href="/en/properties/abu-dhabi/new-project">New project</a>
        <a href="https://evil.example/en/properties/abu-dhabi/private">Foreign</a>
        <a href="/en/properties/dubai/other">Other territory</a>
        <a href="/en/properties/abu-dhabi/">Index</a>
        <a href="/en/properties/abu-dhabi/project?token=secret">Signed</a>
        <a href="/en/properties/abu-dhabi/project/nested">Nested</a>
        <a href="javascript:alert(1)">Active</a></html>"""
    result = candidates_for(definition, payload)
    assert len(result) == 1
    assert result[0]["title"] == "New project"
    assert "project_id" not in result[0]  # Collection scope does not accept map identity.


def test_aldar_types_are_not_a_cartesian_product_of_bedrooms_and_unit_kinds():
    definition = next(
        row for row in project_registry() if row["slug"] == "baccarat-residences-saadiyat"
    )
    source = definition["sources"][0]
    data = {
        "communityId": definition["record_id"],
        "projectName": definition["name"],
        "communityLocation": "Saadiyat Island",
        "totalUnits": 78,
        "completionDate": "2029-08-31",
        "unitTypes": ["Apartment", "Penthouse", "Retail"],
        "bedrooms": ["2", "4"],
    }
    result = extract_project_source(
        definition, source, {"url": source["url"], "payload": json.dumps({"data": data}).encode()}
    )
    assert result["total_units"] == 78
    assert result["handover"]["original_text"] == "2029-08-31"
    assert {(row["property_type"], row["bedrooms"]) for row in result["typologies"]} == {
        ("apartment", None),
        ("penthouse", None),
    }
    assert "availability" not in result and "price" not in result
    for changed in [
        {"communityId": "foreign"},
        {"communityLocation": "Dubai"},
        {"projectName": "Another project"},
        {"totalUnits": -1},
    ]:
        with pytest.raises(ValueError):
            extract_project_source(
                definition,
                source,
                {
                    "url": source["url"],
                    "payload": json.dumps({"data": {**data, **changed}}).encode(),
                },
            )


def test_replacement_document_links_are_observed_without_fetching_or_approving_files():
    definition = copy.deepcopy(
        next(row for row in project_registry() if row["slug"] == "reem-nine")
    )
    source = definition["sources"][0]
    payload = b"""<html><h1>Reem Nine</h1>
        <a href="https://media.saasproperties.com/Reem-Nine-Brochure-2027.pdf">New brochure</a>
        <a href="https://media.saasproperties.com/Reem-Nine.pdf?signature=temporary">Signed link</a>
        <a href="https://other.example/Reem-Nine.pdf">Other host</a>
        <a href="http://127.0.0.1/private.pdf">Private</a></html>"""
    result = extract_project_source(definition, source, {"url": source["url"], "payload": payload})
    assert len(result["media"]) == 1
    media = result["media"][0]
    assert media["role"] == "brochure"
    assert media["rights_status"] == "reference_only"
    assert media["source_url"].endswith("Reem-Nine-Brochure-2027.pdf")


def test_publisher_statistics_exclude_related_projects_and_footer_media():
    definition = next(row for row in project_registry() if row["slug"] == "reem-nine")
    source = definition["sources"][0]
    payload = b"""<html><h1>Reem Nine</h1><main>
      <div class="flex-col">Units 206</div>
      <div class="flex-col">Property Type Apartments</div>
      <div class="flex-col">Bedrooms 1, 2, 3</div>
      <section class="related-projects"><div class="flex-col">Units 900</div></section>
      <footer><a href="https://media.saasproperties.com/Other-Brochure.pdf">Other</a></footer>
      </main></html>"""
    result = extract_project_source(definition, source, {"url": source["url"], "payload": payload})
    assert result["total_units"] == 206
    assert [row["bedrooms"] for row in result["typologies"]] == [1, 2, 3]
    assert result["media"] == []
    with pytest.raises(ValueError, match="Conflicting programme totals"):
        extract_project_source(
            definition,
            source,
            {
                "url": source["url"],
                "payload": payload.replace(
                    b"</main>", b'<div class="flex-col">Units 207</div></main>'
                ),
            },
        )


def test_bloom_cards_preserve_townhouse_type_without_inventing_availability():
    definition = next(row for row in project_registry() if row["slug"] == "soho-square")
    source = definition["sources"][0]
    payload = b"""<html><h1>Soho Square</h1><main>
      <div class="fade-up-text">304 units</div>
      <div class="unit"><h3>Apartments</h3><span>Studio, 45 sqm</span></div>
      <div class="unit"><h3>Townhouses</h3><span>3 Bedrooms, Sold Out</span></div>
      </main></html>"""
    result = extract_project_source(definition, source, {"url": source["url"], "payload": payload})
    assert result["total_units"] == 304
    assert {(row["property_type"], row["bedrooms"]) for row in result["typologies"]} == {
        ("apartment", 0),
        ("townhouse", 3),
    }
    assert "availability" not in result
