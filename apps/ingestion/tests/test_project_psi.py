"""Agency identity, attribution and location safeguards on inert public page fixtures."""

import hashlib
import json

import pytest
from property_platform.modules.evidence.projects.project_discovery import (
    candidates_for,
    catalogue_registry,
)
from property_platform.modules.evidence.projects.project_protocol import (
    extract_project_source,
    project_registry,
    project_urls,
)
from property_platform.modules.evidence.projects.project_psi import psi_position, psi_record


def fixture():
    project = project_registry("al-reem-island:renad-tower")[0]
    source = next(row for row in project["sources"] if row["parser"] == "psi_project_v1")
    row = {
        "propertyId": int(source["record_id"]),
        "propertyName": source["heading_aliases"][0],
        "community": "Al Reem Island",
        "city": "Abu Dhabi",
        "developerName": source["developer_aliases"][0],
        "latitude": 24.5003,
        "longitude": 54.394,
        "handoverDate": "2027-06-30",
        "unitTypes": ["Apartment"],
        "availableBedrooms": [1, 2, 3],
        "facilities": ["Gymnasium", "Swimming pool"],
        "amenities": [],
        "expectedRoi": 33,
        "numberOfApartments": 3,
        "priceRange": {"from": 999},
    }
    return project, source, row


def payload(row):
    text = '6:["$","$L27",null,{"data":' + json.dumps(row) + "}]"
    # The organization position must never be mistaken for the project's point.
    office = '<script type="application/ld+json">{"geo":{"latitude":1,"longitude":2}}</script>'
    return (
        "<html>"
        + office
        + "<script>self.__next_f.push("
        + json.dumps([1, text])
        + ")</script></html>"
    ).encode()


def extract(project, source, row):
    return extract_project_source(project, source, {"url": source["url"], "payload": payload(row)})


def test_public_agency_data_preserve_identity_and_do_not_claim_inventory_or_returns():
    project, source, row = fixture()
    result = extract(project, source, row)
    assert result["handover"]["original_text"] == "2027-06-30"
    assert [r["bedrooms"] for r in result["typologies"]] == [1, 2, 3]
    assert result["total_units"] is None  # Listing counts are not programme totals.
    assert not {"price", "expectedRoi", "availability"} & result.keys()
    marker = psi_position(project, source, payload(row))
    assert marker["lat"] == 24.5003 and marker["lon"] == 54.394
    assert marker["source_kind"] == "broker"
    assert marker["source_name"] == "Property Shop Investment (PSI)"


@pytest.mark.parametrize(
    "field,value",
    [
        ("propertyId", 1),
        ("propertyName", "A different tower"),
        ("community", "Yas Island"),
        ("city", "Dubai"),
        ("developerName", "Another developer"),
    ],
)
def test_changed_agency_identity_is_rejected(field, value):
    project, source, row = fixture()
    row[field] = value
    with pytest.raises(ValueError, match="identity, developer or territory"):
        extract(project, source, row)


def test_default_island_point_and_unavailable_pages_do_not_create_a_location():
    project, source, row = fixture()
    row.update(latitude=24.4942437, longitude=54.4068603)
    assert psi_position(project, source, payload(row)) is None
    with pytest.raises(ValueError, match="absent or ambiguous"):
        psi_record(b"<html><h1>Project details unavailable</h1></html>")


def test_separate_type_and_bedroom_lists_never_invent_combinations():
    project, source, row = fixture()
    row["unitTypes"] = ["Apartment", "Penthouse"]
    result = extract(project, source, row)
    assert {(r["property_type"], r["bedrooms"]) for r in result["typologies"]} == {
        ("apartment", None),
        ("penthouse", None),
    }


def test_per_source_scope_keeps_reviewed_terms_and_refuses_a_forged_source():
    project = project_registry("al-reem-island:the-district")[0]
    source = project["sources"][0]
    key = hashlib.sha256(source["url"].encode()).hexdigest()
    selected = project_registry("al-reem-island:the-district:" + key)
    assert set(project_urls(selected)) == {source["url"], source["terms_url"]}
    with pytest.raises(ValueError, match="not registered"):
        project_registry("al-reem-island:the-district:" + "0" * 64)
    selected[0]["sources"] = [source]
    with pytest.raises(ValueError, match="terms are absent"):
        project_urls(selected)


def test_sitemap_discovers_projects_without_registering_unit_or_neighbouring_island_pages():
    definition = next(r for r in catalogue_registry() if r["key"] == "psi-al-reem-island")
    prefix = definition["prefixes"][0]
    urls = [prefix + "test-tower-500001", prefix + "test-tower-500001/floor-plan"]
    urls += [prefix.replace("al-reem-island", "saadiyat-island") + "other-500002"]
    xml = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    xml += "".join(f"<url><loc>{url}</loc></url>" for url in urls) + "</urlset>"
    result = candidates_for(definition, xml.encode())
    assert len(result) == 1 and result[0]["source_record_id"] == "500001"
    assert "project" not in result[0]
