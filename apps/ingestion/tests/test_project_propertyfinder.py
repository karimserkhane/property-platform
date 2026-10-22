"""Public portal evidence: precise identity, conservative dates and project-only pins."""

import copy
import json

import pytest
from property_platform.modules.evidence.project_discovery import candidates_for, catalogue_for
from property_platform.modules.evidence.project_propertyfinder import (
    propertyfinder_position,
    propertyfinder_project,
)
from property_platform.modules.evidence.project_protocol import _base


def fixture():
    source = {
        "url": "https://www.propertyfinder.ae/en/new-projects/gefinor-limited/canal-by-m",
        "record_id": "fdc92675-f0b1-4245-832c-70d490500e51",
        "role": "project",
        "heading_aliases": ["Canal by M"],
        "developer_aliases": ["GEFINOR LIMITED"],
        "rights_status": "restricted",
        "terms_url": "",
        "acquisition_scope": "local_research",
    }
    project = {"slug": "canal-by-m", "name": "Canal by M", "territory_id": "al-reem-island"}
    data = {
        "id": source["record_id"],
        "title": "Canal by M",
        "slug": "gefinor-limited/canal-by-m",
        "developer": {"name": "GEFINOR LIMITED"},
        "deliveryDate": "2026-09-01T03:36:00Z",
        "locationTree": [{"id": 6, "type": "CITY"}, {"id": 279, "type": "COMMUNITY"}],
        "location": {
            "type": "TOWER",
            "name": "Canal By M",
            "coordinates": {"lat": 24.4984, "lon": 54.4091},
        },
        "stockAvailability": 44,
        "startingPrice": 2600000,
        "units": [
            {
                "units": [
                    {"propertyType": "apartment", "list": [{"bedrooms": 2, "totalUnits": 44}]},
                    {"propertyType": "townhouse", "list": [{"bedrooms": 3}]},
                ]
            }
        ],
    }
    return project, source, data


def payload(data):
    value = {"props": {"pageProps": {"detailResult": data}}}
    return (
        '<html><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(value)
        + "</script></html>"
    ).encode()


def test_floorplan_type_pairs_are_not_inventory_and_delivery_keeps_only_displayed_month():
    project, source, data = fixture()
    result = propertyfinder_project(project, source, {"payload": payload(data)}, _base)
    assert result["handover"]["precision"] == "month" and result["handover"]["day"] is None
    assert result["source_developer_role"] == "declared"
    assert {(r["property_type"], r["bedrooms"]) for r in result["typologies"]} == {
        ("apartment", 2),
        ("townhouse", 3),
    }
    assert result["total_units"] is None and "price" not in result and "availability" not in result


def test_community_and_near_default_tower_points_never_become_project_pins():
    project, source, data = fixture()
    assert (
        propertyfinder_position(project, source, payload(data))["publisher_key"] == "propertyfinder"
    )
    for change in [
        {"type": "COMMUNITY"},
        {"name": "Other project"},
        {"coordinates": {"lat": 24.4943267, "lon": 54.4069032}},
    ]:
        invalid = copy.deepcopy(data)
        invalid["location"].update(change)
        assert propertyfinder_position(project, source, payload(invalid)) is None


@pytest.mark.parametrize(
    "change",
    [
        {"id": "foreign"},
        {"title": "Other project"},
        {"developer": {"name": "Other entity"}},
        {"locationTree": [{"id": 310, "type": "COMMUNITY"}]},
    ],
)
def test_project_party_or_island_changes_fail_before_import(change):
    project, source, data = fixture()
    with pytest.raises(ValueError, match="identity, party or territory"):
        propertyfinder_project(project, source, {"payload": payload({**data, **change})}, _base)


def test_catalogue_counts_pagination_and_unique_ids_are_required_before_discovery():
    definition = catalogue_for("al-reem-island:propertyfinder-al-reem-island-1")
    _, _, record = fixture()
    record["shareUrl"] = "/en/new-projects/gefinor-limited/canal-by-m"
    result = {
        "data": {"projects": [record], "locationTitle": "Al Reem Island"},
        "meta": {"count": {"total": 1}, "pagination": {"page": 1, "total": 1}},
    }

    def document(data):
        return (
            '<html><script id="__NEXT_DATA__">'
            + json.dumps({"props": {"pageProps": {"searchResult": data}}})
            + "</script></html>"
        ).encode()

    assert candidates_for(definition, document(result))[0]["source_record_id"] == record["id"]
    invalid = copy.deepcopy(result)
    invalid["meta"]["pagination"]["page"] = 2
    with pytest.raises(ValueError, match="pagination or island"):
        candidates_for(definition, document(invalid))
    invalid = copy.deepcopy(result)
    invalid["data"]["projects"].append(record)
    invalid["meta"]["count"]["total"] = 2
    with pytest.raises(ValueError, match="identity"):
        candidates_for(definition, document(invalid))
