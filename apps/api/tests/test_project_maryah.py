"""Pure source regressions: no database, network or copied source publications."""

from copy import deepcopy

import pytest

from property_platform.modules.evidence.project_maryah import enrich_maryah

RITZ = (
    "ritz-carlton-residences-al-maryah-island",
    "https://rcalmaryahisland.com/",
)
FOUR_SEASONS = (
    "four-seasons-private-residences-al-maryah-island",
    "https://press.fourseasons.com/abudhabi/hotel-facts/",
)
ROSEWOOD = (
    "rosewood-residences-abu-dhabi",
    "https://www.mubadala.com/en/what-we-do/rosewood-abu-dhabi",
)
JUMEIRAH = (
    "jumeirah-residences-al-maryah-island",
    "https://jumeirah.emiratesdevelopments.com/the-project/",
)


def extract(identity, html, *, project_changes=None, source_changes=None, result=None):
    slug, url = identity
    project = {"slug": slug, "territory_id": "al-maryah-island", **(project_changes or {})}
    source = {
        "url": url,
        "role": "project",
        "source_kind": "developer",
        **(source_changes or {}),
    }
    return enrich_maryah(
        project,
        source,
        html.encode("utf-8"),
        {"total_units": None, "handover": None, "typologies": [], **(result or {})},
    )


def test_ritz_accepts_identical_responsive_claims_but_not_copied_catalogue_total():
    html = '<div class="t480__uptitle">The collection comprises 165 exquisite private homes</div>'
    result = extract(RITZ, html * 2 + "<p>St. Regis residences: 161</p>")
    assert result["total_units"] == 165
    assert result["total_units_basis"] == "announced"
    assert "165 exquisite private homes" in result["total_units_original"]
    assert result["handover"] is None


def test_ritz_disagreement_requires_a_source_review():
    html = '<div class="t480__uptitle">The collection comprises {} exquisite private homes</div>'
    with pytest.raises(ValueError, match="absent or ambiguous"):
        extract(RITZ, html.format(165) + html.format(161))


def test_four_seasons_residential_units_are_not_hotel_guest_rooms():
    result = extract(
        FOUR_SEASONS,
        "<h1>Opening Date May 2016</h1><p>Total Number of Guest Rooms: 200</p>"
        "<p>Residences: Spanning floors 15 through 34, the Hotel features a mix of "
        "124 residential units, which consists of 39 one-bedroom units.</p>",
        source_changes={"source_kind": "publisher"},
    )
    assert result["total_units"] == 124
    assert result["handover"] is None
    # The paragraph does not establish whether each residence is an apartment or duplex.
    assert result["typologies"] == []


def test_hotel_only_total_cannot_substitute_for_missing_residential_claim():
    with pytest.raises(ValueError, match="absent or ambiguous"):
        extract(FOUR_SEASONS, "<p>Total Number of Guest Rooms: 200</p>")


def test_rosewood_accepts_serviced_residences_and_ignores_rooms_and_suites():
    result = extract(
        ROSEWOOD,
        "<p>Rosewood Abu Dhabi features 154 spacious rooms, 35 suites and "
        "131 serviced residences.</p>",
    )
    assert result["total_units"] == 131
    assert result["total_units_original"] == "131 serviced residences"


def test_jumeirah_preserves_explicit_type_pairs_with_elementor_body_class():
    html = (
        '<html><body class="elementor_header_footer"><p>'
        "Jumeirah Residences Al Maryah Island offers a selection of light- filled "
        "one to four bedroom apartments and five bedroom penthouses, each with "
        "its own private terrace.</p></body></html>"
    )
    result = extract(JUMEIRAH, html)
    assert [(row["property_type"], row["bedrooms"]) for row in result["typologies"]] == [
        ("apartment", 1),
        ("apartment", 2),
        ("apartment", 3),
        ("apartment", 4),
        ("penthouse", 5),
    ]
    assert all("HTML:p[" in row["evidence_pointer"] for row in result["typologies"])
    assert all(
        "one to four bedroom apartments" in row["original_text"] for row in result["typologies"]
    )


@pytest.mark.parametrize("tag", ["script", "footer", "header", "nav", "form"])
def test_non_project_markup_cannot_supply_residential_totals(tag):
    html = f"<{tag}><p>Residences: a mix of 124 residential units</p></{tag}>"
    with pytest.raises(ValueError, match="absent or ambiguous"):
        extract(FOUR_SEASONS, html)


@pytest.mark.parametrize(
    ("project_changes", "source_changes"),
    [
        ({"territory_id": "saadiyat-island"}, {}),
        ({"slug": "a-different-project"}, {}),
        ({}, {"url": "https://example.com/"}),
        ({}, {"source_kind": "broker"}),
        ({}, {"role": "terms"}),
    ],
)
def test_rules_do_not_spill_to_other_identities_or_sources(project_changes, source_changes):
    result = extract(
        FOUR_SEASONS,
        "<p>Residences: a mix of 124 residential units</p>",
        project_changes=project_changes,
        source_changes=source_changes,
    )
    assert result == {"total_units": None, "handover": None, "typologies": []}


def test_enrichment_does_not_mutate_the_generic_result_or_duplicate_typologies():
    original = {
        "total_units": None,
        "handover": None,
        "typologies": [
            {
                "property_type": "apartment",
                "bedrooms": 1,
                "original_text": "original proof",
                "evidence_pointer": "original location",
            }
        ],
    }
    before = deepcopy(original)
    result = extract(
        JUMEIRAH,
        "<p>Jumeirah Residences Al Maryah Island offers "
        "one to four bedroom apartments and five bedroom penthouses</p>",
        result=original,
    )
    assert original == before
    assert len(result["typologies"]) == 5
    assert result["typologies"][0]["original_text"] == "original proof"
