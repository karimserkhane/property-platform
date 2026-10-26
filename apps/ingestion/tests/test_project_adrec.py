"""Project-register identities and residential counts, without marketing inference."""

import copy
import json

import pytest
from property_platform.modules.evidence.projects.project_adrec import adrec_position, adrec_project
from property_platform.modules.evidence.projects.project_protocol import _base


def fixture():
    source = {
        "url": "https://adrec.gov.ae/api/feature/Profession/ProjectDetail?id=669",
        "record_id": "669",
        "registration_number": "20250000731926",
        "district_id": 2540,
        "heading_aliases": ["Sensi"],
        "developer_aliases": ["NOVA MIDDLE EAST PROPERTY INVESTMENT - L.L.C - S.P.C"],
        "role": "project",
        "rights_status": "restricted",
        "terms_url": None,
        "acquisition_scope": "local_research",
        "fact_scope": "project",
    }
    project = {
        "slug": "sensi",
        "name": "Sensi",
        "territory_id": "saadiyat-island",
        "sources": [source],
        "developer": {"name": "Reportage Properties"},
    }
    record = {
        "Id": 669,
        "ProjectNumber": "20250000731926",
        "MunicipalityId": 1000,
        "DistrictId": 2540,
        "DistrictEn": "Al Saadiyat Island",
        "Name": "Sensi ",
        "DeveloperName": source["developer_aliases"][0],
        "Description": "<p>Registered residential development.</p><script>not a fact</script>",
        "ResidentialUnits": 89,
        "UnitCount": 999,
        "totalCount": 1000,
        "EndDate": "/Date(1893456000000)/",
        "Latitude": 24.54,
        "Longitude": 54.43,
        "PropertyProjectUnits": [
            {"Type": "APARTMENT", "TwoBedroom": 43, "ThreeBedroom": 37, "FourBedroom": 0},
            {"Type": "VILLA", "FourBedroom": 9, "TwoBedroom": None},
        ],
    }
    return project, source, record


def payload(record):
    return json.dumps({"Success": True, "Data": {"Result": record}}).encode()


def test_registered_residential_count_and_party_are_distinct_from_brand_and_inventory():
    project, source, record = fixture()
    result = adrec_project(project, source, {"payload": payload(record)}, _base)
    assert result["total_units"] == 89  # Neither listing total nor UnitCount.
    assert result["total_units_basis"] == "registered"
    assert result["source_developer_name"].startswith("NOVA MIDDLE EAST")
    assert result["source_developer_role"] == "registered"
    assert project["developer"]["name"] == "Reportage Properties"  # No legal-entity merge.
    assert result["summary"] == "Registered residential development."
    assert result["handover"] is None  # EndDate has no reviewed handover meaning.
    assert {(r["property_type"], r["bedrooms"]) for r in result["typologies"]} == {
        ("apartment", 2),
        ("apartment", 3),
        ("villa", 4),
    }
    assert "price" not in result and "availability" not in result


def test_component_registration_never_supplies_the_whole_parent_total_or_summary():
    project, source, record = fixture()
    source["fact_scope"] = "identity_only"
    result = adrec_project(project, source, {"payload": payload(record)}, _base)
    assert result["total_units"] is None and result["summary"] == ""
    assert result["typologies"]
    assert adrec_position(project, source, payload(record)) is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("Id", 1),
        ("ProjectNumber", "other"),
        ("DistrictId", 1347),
        ("DistrictEn", "Yas Island"),
        ("MunicipalityId", 1001),
        ("Name", "Other development"),
        ("DeveloperName", "Unreviewed party"),
    ],
)
def test_an_authority_identity_or_scope_change_fails_before_database_mutation(field, value):
    project, source, record = fixture()
    record[field] = value
    with pytest.raises(ValueError, match="registration, party or territory"):
        adrec_project(project, source, {"payload": payload(record)}, _base)


def test_only_declared_coordinates_are_returned_and_missing_coordinates_stay_missing():
    project, source, record = fixture()
    marker = adrec_position(project, source, payload(record))
    assert marker["lat"] == 24.54 and marker["source_kind"] == "authority"
    record["Latitude"] = None
    assert adrec_position(project, source, payload(record)) is None
    changed = copy.deepcopy(source)
    changed["url"] += "&district=2540"
    with pytest.raises(ValueError, match="registration"):
        adrec_position(project, changed, payload(record))
