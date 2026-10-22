"""Narrow first-party Al Maryah facts from explicitly reviewed project pages.

The existing official-page extractor validates each identity first. These rules
only add facts whose wording distinguishes residences from hotel accommodation;
they do not infer completion, prices, availability or type/bedroom cross-products.
"""

import re
from copy import deepcopy

_RULES = {
    (
        "ritz-carlton-residences-al-maryah-island",
        "https://rcalmaryahisland.com/",
    ): "ritz",
    (
        "four-seasons-private-residences-al-maryah-island",
        "https://press.fourseasons.com/abudhabi/hotel-facts/",
    ): "four_seasons",
    (
        "rosewood-residences-abu-dhabi",
        "https://www.mubadala.com/en/what-we-do/rosewood-abu-dhabi",
    ): "rosewood",
    (
        "jumeirah-residences-al-maryah-island",
        "https://jumeirah.emiratesdevelopments.com/the-project/",
    ): "jumeirah",
}
_SKIP = frozenset({"header", "footer", "nav", "form", "script", "style", "noscript", "template"})


def _visible_nodes(payload):
    from .project_protocol import MAX_CAPTURE_BYTES, _Document

    if type(payload) is not bytes or not 0 < len(payload) <= MAX_CAPTURE_BYTES:
        raise ValueError("Al Maryah project source exceeds its response budget")

    def walk(node):
        if node.tag in _SKIP:
            return
        yield node
        for child in node.children:
            if not isinstance(child, str):
                yield from walk(child)

    return tuple(walk(_Document(payload).root))


def _unique_claim(nodes, pattern, *, tag, css_class=None, prefix=None):
    expression = re.compile(pattern, re.I)
    claims = []
    for index, node in enumerate(nodes):
        if node.tag != tag or (css_class and not node.has_class(css_class)):
            continue
        text = node.text()
        if prefix and not text.startswith(prefix):
            continue
        for match in expression.finditer(text):
            claims.append((match.group(1), match.group(0), f"HTML:{tag}[{index}]:{pattern}"))
    # Identical responsive copies are one assertion. Disagreement is a schema
    # review, not permission to choose the largest or latest visible number.
    if len({claim[0] for claim in claims}) != 1:
        raise ValueError("Reviewed Al Maryah residential claim is absent or ambiguous")
    return claims[0]


def _residential_total(result, claim):
    value, original, pointer = claim
    count = int(value)
    if not 0 < count <= 100000:
        raise ValueError("Al Maryah residential total is outside its accepted range")
    result.update(
        total_units=count,
        total_units_basis="announced",
        total_units_original=original,
        total_units_pointer=pointer,
    )


def enrich_maryah(project, source, payload, result):
    """Return an independent official result enriched by exact reviewed source rules."""
    enriched = deepcopy(result)
    rule = _RULES.get((project.get("slug"), source.get("url")))
    if (
        rule is None
        or project.get("territory_id") != "al-maryah-island"
        or source.get("role") != "project"
        or source.get("source_kind") not in {"developer", "publisher"}
    ):
        return enriched
    nodes = _visible_nodes(payload)
    enriched["parser_version"] = "maryah-first-party-v1"
    if rule == "ritz":
        _residential_total(
            enriched,
            _unique_claim(
                nodes,
                r"The collection comprises ([1-9]\d{0,5}) exquisite private homes",
                tag="div",
                css_class="t480__uptitle",
            ),
        )
    elif rule == "four_seasons":
        _residential_total(
            enriched,
            _unique_claim(
                nodes,
                r"a mix of ([1-9]\d{0,5}) residential units",
                tag="p",
                prefix="Residences:",
            ),
        )
    elif rule == "rosewood":
        _residential_total(
            enriched,
            _unique_claim(
                nodes,
                r"([1-9]\d{0,5}) serviced residences",
                tag="p",
                prefix="Rosewood Abu Dhabi features ",
            ),
        )
    else:
        _, original, pointer = _unique_claim(
            nodes,
            r"(one to four bedroom apartments and five bedroom penthouses)",
            tag="p",
            prefix="Jumeirah Residences Al Maryah Island offers ",
        )
        for kind, beds in [("apartment", bed) for bed in range(1, 5)] + [("penthouse", 5)]:
            if not any(
                row["property_type"] == kind and row["bedrooms"] == beds
                for row in enriched["typologies"]
            ):
                enriched["typologies"].append(
                    {
                        "property_type": kind,
                        "bedrooms": beds,
                        "original_text": original,
                        "evidence_pointer": pointer,
                    }
                )
    return enriched
