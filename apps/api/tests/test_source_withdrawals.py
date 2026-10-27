import json
import re

import pytest

from property_platform.modules.evidence import source_withdrawals
from property_platform.modules.evidence.projects.project_protocol import REGISTRIES
from property_platform.modules.evidence.source_withdrawals import (
    capture_url_pattern,
    is_withdrawn,
    link_allowed,
    validate_withdrawals,
    withdrawal,
    withdrawals,
)

DECISION = {
    "host": "example.com",
    "publisher": "Example",
    "decided_on": "2026-10-27",
    "decided_by": "Karim",
    "reason": "Terms forbid automated collection.",
    "links": False,
}


def registry_urls():
    """Every URL field of the reviewed JSON registries at the evidence root."""
    urls = []

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.endswith("url") and isinstance(item, str) and item:
                    urls.append(item)
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for path in sorted(REGISTRIES.glob("*.json")):
        walk(json.loads(path.read_text("utf-8")))
    return urls


def test_the_owner_decisions_of_27_october_are_recorded():
    assert {row["host"]: row["links"] for row in withdrawals()} == {
        "propertyfinder.ae": False,
        "psinv.net": False,
        "aldar.com": True,
        "linkedin.com": False,
        "reddit.com": False,
    }
    assert {row["decided_on"] for row in withdrawals()} == {"2026-10-27"}


@pytest.mark.parametrize(
    ("url", "host"),
    [
        ("https://www.propertyfinder.ae/en/new-projects/x", "propertyfinder.ae"),
        ("https://psinv.net/en/projects/abu-dhabi/x-1", "psinv.net"),
        ("https://searchservice.properties.aldar.com/api/v1/x", "aldar.com"),
        ("https://WWW.ALDAR.COM/en/x", "aldar.com"),
        ("https://ae.linkedin.com/company/x", "linkedin.com"),
        ("https://www.reddit.com/r/x/comments/y", "reddit.com"),
    ],
)
def test_a_decision_covers_its_host_and_subdomains(url, host):
    assert withdrawal(url)["host"] == host
    assert re.match(capture_url_pattern(), url, re.IGNORECASE)


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
def test_other_sites_and_lookalikes_are_not_withdrawn(url):
    assert not is_withdrawn(url)
    assert link_allowed(url)
    if isinstance(url, str):
        assert not re.match(capture_url_pattern(), url, re.IGNORECASE)


def test_only_aldar_pages_keep_plain_links():
    assert link_allowed("https://www.aldar.com/properties/en/uae/reem-island/gate")
    assert not link_allowed("https://psinv.net/en/projects/x")
    assert not link_allowed("https://www.propertyfinder.ae/en/x")


def test_each_decision_covers_registered_sources_and_the_pattern_agrees():
    urls = registry_urls()
    covered = {withdrawal(url)["host"] for url in urls if is_withdrawn(url)}
    # A mistyped host would withdraw nothing and silently keep the collection running.
    assert covered == {row["host"] for row in withdrawals()}
    for url in urls:
        assert bool(re.match(capture_url_pattern(), url, re.IGNORECASE)) is is_withdrawn(url)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"host": "www.example.com"}, "registrable host"),
        ({"host": "example"}, "registrable host"),
        ({"links": "no"}, "plain links"),
        ({"reason": " "}, "reason"),
        ({"decided_on": "27/10/2026"}, "Invalid isoformat"),
    ],
)
def test_malformed_decisions_are_refused(change, message):
    with pytest.raises(ValueError, match=message):
        validate_withdrawals([{**DECISION, **change}])


def test_duplicate_nested_or_incomplete_decisions_are_refused():
    with pytest.raises(ValueError, match="Duplicate"):
        validate_withdrawals([DECISION, DECISION])
    with pytest.raises(ValueError, match="cover another"):
        validate_withdrawals([DECISION, {**DECISION, "host": "shop.example.com"}])
    with pytest.raises(ValueError, match="Unexpected"):
        validate_withdrawals([{key: value for key, value in DECISION.items() if key != "links"}])


def test_without_decisions_nothing_is_withdrawn(monkeypatch):
    monkeypatch.setattr(source_withdrawals, "withdrawals", lambda: ())
    assert capture_url_pattern() is None
    assert not is_withdrawn("https://psinv.net/en/projects/x")
