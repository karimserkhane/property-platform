import json
import re

import pytest

from property_platform.modules.evidence import source_rights as rights_module
from property_platform.modules.evidence.maps import (
    accessibility,
    map_sources,
    onwani,
    osm_api_protocol,
    overture_protocol,
    sdi_protocol,
)
from property_platform.modules.evidence.projects import activity_import
from property_platform.modules.evidence.projects.project_protocol import REGISTRIES
from property_platform.modules.evidence.source_rights import (
    DEFAULT,
    collection_allowed,
    enforcement,
    facts_allowed,
    link_allowed,
    public_rights,
    rights_for,
    source_rights,
    validate_enforcement,
    validate_source_rights,
    withheld_capture_pattern,
)
from property_platform.modules.evidence.sources import abu_dhabi, adrec, imagery_import

REVIEW = {
    "host": "example.com",
    "publisher": "Example",
    "licence": "proprietary",
    "licence_url": "",
    "terms_url": "https://example.com/terms",
    "reviewed_on": "2026-10-27",
    "reviewed_by": "Karim",
    "collection": "forbidden",
    "publication": "none",
    "attribution": "",
    "basis": "Terms forbid automated collection.",
}
DECISION = {"enforced": True, "decided_on": "2026-10-27", "decided_by": "Karim", "basis": "Test."}
# Endpoints the connectors contact, outside the JSON registries.
CONNECTORS = (
    onwani.BASE_URL,
    abu_dhabi.DISTRICT_BASE,
    sdi_protocol.URL,
    map_sources.OSM_URL,
    map_sources.OSM_MIRROR,
    osm_api_protocol.URL,
    overture_protocol.URL,
    accessibility.GRAPH_URL,
    activity_import.SOURCE_URL,
    imagery_import.BASE,
    adrec.BASE,
    "https://stac.overturemaps.org/",
    "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/",
    "https://tiles.openfreemap.org/planet/latest",
    "https://wmts.terrascope.be/wmts",
    "https://stem.doh.gov.ae/HFMap/Home/GetAllFacilities",
    "https://charterschools.abudhabi/find-a-school",
    "https://admobility.gov.ae/en/pb-bus-service/",
    "https://census.scad.gov.ae/home/realestate?lang=en",
)


def registry_urls():
    """Every source URL field of the reviewed JSON registries at the evidence root."""
    urls = []

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                # A licence URL names a licence text, not a source.
                if key.endswith("url") and key != "licence_url" and isinstance(item, str):
                    if item:
                        urls.append(item)
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for path in sorted(REGISTRIES.glob("*.json")):
        if not path.name.startswith("source_rights"):
            walk(json.loads(path.read_text("utf-8")))
    return urls


def test_every_source_and_connector_has_an_explicit_review_entry():
    urls = registry_urls() + list(CONNECTORS)
    missing = sorted({url for url in urls if rights_for(url) is DEFAULT})
    assert missing == []
    # A stale entry would describe a site no pipeline reads any more.
    used = {rights_for(url)["host"] for url in urls}
    assert {row["host"] for row in source_rights()} == used


def test_the_owner_decisions_of_27_october_are_recorded():
    decided = {
        row["host"]: (row["collection"], row["publication"])
        for row in source_rights()
        if row["collection"] == "forbidden"
    }
    assert decided == {
        "aldar.com": ("forbidden", "link"),
        "bayut.com": ("forbidden", "none"),
        "linkedin.com": ("forbidden", "none"),
        "propertyfinder.ae": ("forbidden", "none"),
        "psinv.net": ("forbidden", "none"),
        "reddit.com": ("forbidden", "none"),
    }


def test_the_owner_collects_and_shows_every_source_with_its_rights_recorded():
    decisions = enforcement()
    assert decisions["publication"]["enforced"] is False
    assert decisions["collection"]["enforced"] is False
    assert {decision["decided_by"] for decision in decisions.values()} == {"Karim"}
    url = "https://psinv.net/en/projects/abu-dhabi/x-1"
    assert collection_allowed(url) and facts_allowed(url)
    assert rights_for(url)["collection"] == "forbidden"


def test_unenforced_publication_shows_withheld_sites_and_still_reports_their_rights(
    enforce_rights,
):
    enforce_rights(collection=True, publication=False)
    url = "https://psinv.net/en/projects/abu-dhabi/x-1"
    assert facts_allowed(url) and link_allowed(url)
    assert withheld_capture_pattern() is None
    assert public_rights(url)["publication"] == "none"
    assert public_rights(url)["terms_url"] == "https://psinv.net/en/terms"
    assert not collection_allowed(url)


def test_unenforced_collection_reaches_every_site(enforce_rights):
    enforce_rights(collection=False, publication=True)
    assert collection_allowed("https://www.propertyfinder.ae/en/new-projects/x")
    assert not facts_allowed("https://www.propertyfinder.ae/en/new-projects/x")
    assert rights_for("https://www.propertyfinder.ae/")["collection"] == "forbidden"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"enforced": 0}, "enforced or not"),
        ({"reason": "x"}, "Unexpected enforcement"),
        ({"decided_on": None}, "dated"),
        ({"decided_on": "27/10/2026"}, "Invalid isoformat"),
        ({"decided_by": " "}, "names who"),
        ({"basis": ""}, "names who"),
    ],
)
def test_malformed_enforcement_decisions_are_refused(change, message):
    with pytest.raises(ValueError, match=message):
        validate_enforcement({"collection": DECISION, "publication": {**DECISION, **change}})
    with pytest.raises(ValueError, match="collection and publication"):
        validate_enforcement({"collection": DECISION})


def test_open_data_keep_their_licence_and_attribution():
    osm = rights_for("https://api.openstreetmap.org/api/0.6/map")
    assert (osm["licence"], osm["publication"]) == ("ODbL-1.0", "open")
    assert osm["attribution"] == "© OpenStreetMap contributors"
    assert rights_for(overture_protocol.URL)["licence"] == "CDLA-Permissive-2.0"
    assert rights_for("https://wmts.terrascope.be/wmts")["licence"] == "CC-BY-4.0"
    assert public_rights(onwani.BASE_URL) == {
        "licence": "unknown",
        "licence_url": None,
        "terms_url": None,
        "publication": "facts",
        "attribution": None,
        "reviewed_on": None,
    }


@pytest.mark.parametrize(
    ("url", "host"),
    [
        ("https://www.propertyfinder.ae/en/new-projects/x", "propertyfinder.ae"),
        ("https://psinv.net/en/projects/abu-dhabi/x-1", "psinv.net"),
        ("https://searchservice.properties.aldar.com/api/v1/x", "aldar.com"),
        ("https://WWW.ALDAR.COM/en/x", "aldar.com"),
        ("https://ae.linkedin.com/company/x", "linkedin.com"),
        ("https://www.reddit.com/r/x/comments/y", "reddit.com"),
        ("https://www.bayut.com/buildings/x/", "bayut.com"),
    ],
)
@pytest.mark.usefixtures("enforced_rights")
def test_a_review_covers_its_host_and_subdomains(url, host):
    assert rights_for(url)["host"] == host
    assert not collection_allowed(url) and not facts_allowed(url)
    assert re.match(withheld_capture_pattern(), url, re.IGNORECASE)


@pytest.mark.parametrize(
    "url",
    [
        "https://notaldar.com/x",
        "https://aldar.com.example.org/x",
        "https://example.org/?next=https://psinv.net/",
        "https://reportagegroup.com/projects/x/",
        "https://adrec.gov.ae/api/feature/x",
        "not a url",
        None,
    ],
)
@pytest.mark.usefixtures("enforced_rights")
def test_other_sites_and_lookalikes_keep_their_own_rights(url):
    assert collection_allowed(url) and facts_allowed(url) and link_allowed(url)
    if isinstance(url, str):
        assert not re.match(withheld_capture_pattern(), url, re.IGNORECASE)


@pytest.mark.usefixtures("enforced_rights")
def test_only_aldar_pages_keep_plain_links_among_withheld_sites():
    assert link_allowed("https://www.aldar.com/properties/en/uae/reem-island/gate")
    assert not link_allowed("https://psinv.net/en/projects/x")
    assert not link_allowed("https://www.propertyfinder.ae/en/x")


@pytest.mark.usefixtures("enforced_rights")
def test_the_postgresql_pattern_agrees_with_every_registered_url():
    for url in registry_urls():
        withheld = bool(re.match(withheld_capture_pattern(), url, re.IGNORECASE))
        assert withheld is not facts_allowed(url)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"host": "www.example.com"}, "without www"),
        ({"host": "example"}, "without www"),
        ({"publication": "public"}, "Unknown collection or publication"),
        ({"reason": "x"}, "Unexpected source rights entry"),
        ({"basis": " "}, "basis"),
        ({"reviewed_on": "27/10/2026"}, "Invalid isoformat"),
        ({"reviewed_on": None}, "Only a review"),
        ({"reviewed_by": " "}, "names who"),
        ({"terms_url": ""}, "cites the terms"),
        ({"terms_url": "http://example.com/terms"}, "HTTPS"),
        ({"collection": "allowed", "publication": "open"}, "open licence"),
    ],
)
def test_malformed_reviews_are_refused(change, message):
    with pytest.raises(ValueError, match=message):
        validate_source_rights([{**REVIEW, **change}])


def test_duplicate_or_nested_hosts_are_refused():
    with pytest.raises(ValueError, match="Duplicate"):
        validate_source_rights([REVIEW, REVIEW])
    with pytest.raises(ValueError, match="nest"):
        validate_source_rights([REVIEW, {**REVIEW, "host": "shop.example.com"}])


@pytest.mark.usefixtures("enforced_rights")
def test_an_unreviewed_host_keeps_the_unqualified_preview_treatment(monkeypatch):
    monkeypatch.setattr(rights_module, "source_rights", lambda: ())
    assert withheld_capture_pattern() is None
    assert rights_for("https://psinv.net/en/projects/x") is DEFAULT
    assert collection_allowed("https://psinv.net/en/projects/x")
    assert public_rights("https://psinv.net/")["licence"] == "unknown"
