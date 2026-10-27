"""Reviewed AD-SDI district scopes: no free SQL, islands keep their archived identity."""

import json
from importlib.resources import files

import pytest

from property_platform.modules.evidence.collection_profiles import COLLECTIONS
from property_platform.modules.evidence.maps import onwani
from property_platform.modules.evidence.maps import sdi_protocol as protocol
from property_platform.modules.evidence.rebuild.failed_acquisitions import source_definition


def test_registry_covers_three_municipalities_and_reuses_island_scopes():
    scopes = protocol.district_scopes()
    assert len(scopes) == 213
    assert {len(protocol.scopes_in(m)) for m in protocol.MUNICIPALITIES} == {98, 69, 46}
    for territory, profile in COLLECTIONS.items():
        assert scopes[territory] == ("ADM", profile.district_name)
        assert f"adm:{profile.slug}" not in scopes


def test_island_clause_and_namespace_are_unchanged_for_archived_captures():
    assert protocol.where("al-maryah-island") == "UPPER(DISTRICTENG)='AL MARYAH ISLAND'"
    assert protocol.namespace("al-reem-island") == "ad-sdi:generic-search:plots:reem"


def test_district_clause_quotes_names_and_separates_homonyms():
    assert protocol.where("aam:al-qou") == "MUNICIPALITYENG='AAM' AND DISTRICTENG='AL QOU'''"
    assert protocol.where("adm:al-bateen") != protocol.where("aam:al-bateen")
    assert protocol.namespace("wrm:mzeerah") == "ad-sdi:generic-search:plots:wrm:mzeerah"
    assert source_definition("sdi_parcels", "adm:khalifa-city")[0].endswith(":adm:khalifa-city")


@pytest.mark.parametrize("scope", ["adm:unknown", "ADM:KHALIFA CITY", "x' OR '1'='1", None])
def test_unregistered_scopes_are_refused(scope):
    with pytest.raises(ValueError, match="Unregistered AD-SDI district scope"):
        protocol.where(scope)
    with pytest.raises(ValueError):
        protocol.scopes_in("DXB")


def test_district_listing_bound_covers_every_reviewed_district():
    raw = json.loads(
        files(protocol.__package__).joinpath("sdi_districts.json").read_text(encoding="utf-8")
    )
    largest = max(row["plots_at_review"] for row in raw["districts"])
    assert onwani.MAX_RECORDS < largest <= protocol.MAX_RECORDS
    assert protocol.object_ids({"objectIds": list(range(largest, 0, -1))})[0] == 1
    with pytest.raises(protocol.SourceError, match="unexpectedly large"):
        protocol.object_ids({"objectIds": list(range(1, protocol.MAX_RECORDS + 2))})
    with pytest.raises(onwani.SourceError, match="unexpectedly large"):
        onwani.object_ids({"objectIds": list(range(1, largest + 1))})
