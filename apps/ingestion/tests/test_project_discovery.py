"""Synthetic publisher contracts: discovery is a review queue, not geospatial identity."""

import copy
import json

import pytest
from property_platform.modules.evidence.project_discovery import (
    candidates_for,
    catalogue_byte_limit,
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


def test_multilingual_psi_sitemap_has_a_reviewed_budget_without_raising_other_sources():
    definition = catalogue_for("al-reem-island:psi-al-reem-island")
    assert catalogue_byte_limit(definition) == 16 * 1024 * 1024
    assert catalogue_byte_limit(catalogue_for("saadiyat-island:aldar-saadiyat")) == 4 * 1024 * 1024
    payload = (
        b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        b"<url><loc>https://psinv.net/en/projects/abu-dhabi/abu-dhabi-district/al-reem-island/reem-diamond-12345</loc></url>"
        + b" " * (4 * 1024 * 1024)
        + b"</urlset>"
    )
    assert candidates_for(definition, payload)[0]["source_record_id"] == "12345"
    with pytest.raises(ValueError, match="response budget"):
        candidates_for(catalogue_for("saadiyat-island:aldar-saadiyat"), payload)


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


def test_adrec_catalogue_requires_complete_territorial_page_and_unique_registrations():
    definition = catalogue_for("saadiyat-island:adrec-saadiyat-register")
    record = {
        "Id": 669,
        "ProjectNumber": "20250000731926",
        "Name": "Sensi",
        "DistrictId": 2540,
        "MunicipalityId": 1000,
    }
    data = {
        "Success": True,
        "Data": {
            "Result": {
                "Projects": [record],
                "RecordsTotal": 1,
                "TotalPages": 1,
                "Number": 0,
            }
        },
    }
    assert candidates_for(definition, json.dumps(data).encode())[0]["source_record_id"] == "669"
    for changed in [
        {"TotalPages": 2},
        {"RecordsTotal": 2},
        {"Number": 1},
        {"Projects": [record, record], "RecordsTotal": 2},
        {"Projects": [{**record, "DistrictId": 1347}]},
    ]:
        invalid = copy.deepcopy(data)
        invalid["Data"]["Result"].update(changed)
        with pytest.raises(ValueError):
            candidates_for(definition, json.dumps(invalid).encode())


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
    assert result["total_units"] == 78  # Publisher's mixed programme units, not 78 homes.
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


def test_publisher_global_brochure_is_not_assigned_to_the_other_canal_project():
    for slug, title, expected in [
        ("canal-by-m", "Canal By M", 1),
        ("canal-residence", "Canal Residence", 0),
    ]:
        definition = project_registry("al-reem-island:" + slug)[0]
        source = next(s for s in definition["sources"] if s["parser"] == "official_project_v1")
        payload = (
            "<html><title>by M</title><body><div>Project | " + title + "</div>"
            '<a href="assets/canal-by-m-e-brochure.pdf">Brochure</a></body></html>'
        ).encode()
        result = extract_project_source(
            definition, source, {"url": source["url"], "payload": payload}
        )
        assert len(result["media"]) == expected
        if expected:
            assert (
                result["media"][0]["source_url"]
                == "https://by-mholding.com/assets/canal-by-m-e-brochure.pdf"
            )
        with pytest.raises(ValueError, match="identity label"):
            extract_project_source(
                definition,
                source,
                {
                    "url": source["url"],
                    "payload": payload.replace(("Project | " + title).encode(), b"Navigation link"),
                },
            )


def test_building_guide_checks_named_party_and_island_and_keeps_only_explicit_type_pairs():
    definition = project_registry("al-reem-island:reem-diamond")[0]
    source = next(s for s in definition["sources"] if s["parser"] == "bayut_guide_v1")
    payload = b"""<html><h1>Reem Diamond</h1><ul>
      <li>Developer: SmartWill Asia</li><li>Location: Al Reem Island</li>
      <li>Unit type: 1, 2 and 3-bedroom apartments</li>
      <li>Number of units: 48</li><li>Date of completion: 2014</li></ul></html>"""
    result = extract_project_source(definition, source, {"url": source["url"], "payload": payload})
    assert result["source_developer_name"] == "SmartWill Asia"
    assert [r["bedrooms"] for r in result["typologies"]] == [1, 2, 3]
    assert result["handover"] is None and result["total_units"] is None
    assert result["media"] == [] and "price" not in result
    for old, new in [(b"SmartWill Asia", b"Other entity"), (b"Al Reem Island", b"Dubai")]:
        with pytest.raises(ValueError, match="developer or island"):
            extract_project_source(
                definition, source, {"url": source["url"], "payload": payload.replace(old, new)}
            )
