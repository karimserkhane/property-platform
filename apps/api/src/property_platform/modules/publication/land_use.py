"""Versioned display taxonomy. Original usage remains visible; unknown is explicit."""

VERSION = "land-use-v3"
CATEGORIES = {
    "mixed": "#d9bf95",
    "residential": "#eedfae",
    "green": "#bfdbb6",
    "public": "#a9ccdf",
    "tech": "#c7cdd3",
    "rail": "#ac83bc",
    "overlay": "#b9a5c3",
    "unknown": "#e7e3d7",
}


def category(value):
    text = value.lower().replace(" ", "")
    if not text:
        return "unknown"
    # AD-SDI publishes broad primary uses through its own reviewed subtype dictionary.
    # Preserve those original words; do not infer a school, hospital or park subtype.
    if text in {
        "educational",
        "health",
        "governmental",
        "cultural",
        "religious",
        "public",
        "diplomatic",
        "recreational",
        "archaeological",
    }:
        return "public"
    if text in {"utility", "industrial", "communication"}:
        return "tech"
    if "projectlimit" in text:
        return "overlay"
    if any(term in text for term in ("rail", "tram")):
        return "rail"
    if any(
        term in text
        for term in ("commercial", "commerical", "retail", "retial", "office", "multiusage")
    ):
        return "mixed"
    if any(
        term in text for term in ("residen", "townhouse", "villa", "multiunit", "employeehousing")
    ):
        return "residential"
    if (
        any(
            term in text
            for term in (
                "garden",
                "park/",
                "publicpark",
                "mixedpark",
                "beach",
                "openspace",
                "naturalarea",
                "publicrealm",
                "outdoor",
            )
        )
        or text == "park"
    ):
        return "green"
    if any(
        term in text
        for term in (
            "school",
            "mosque",
            "masjed",
            "hotel",
            "hospital",
            "universit",
            "club",
            "sport",
            "community",
            "healthcare",
            "science",
            "nursery",
            "postoffice",
            "police",
            "civildefence",
        )
    ):
        return "public"
    if any(
        term in text
        for term in (
            "station",
            "utilities",
            "water",
            "tele",
            "bridge",
            "transport",
            "gas",
            "sew",
            "irrigation",
            "cooling",
            "parking",
            "tank",
            "dock",
            "marina",
            "security",
            "service",
            "datacenter",
            "waste",
            "private",
            "power",
            "busterminal",
            "chlorine",
            "desalination",
            "reservoir",
            "transformer",
        )
    ):
        return "tech"
    return "unknown"
