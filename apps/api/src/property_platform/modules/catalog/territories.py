"""Navigation metadata, not surveyed administrative boundaries or data coverage claims."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Territory:
    id: str
    parent_id: str | None
    level: str
    name: str
    name_ar: str
    bounds: tuple[float, float, float, float]


DEFAULT_TERRITORY_ID = "al-reem-island"
TERRITORIES = (
    Territory(
        "uae",
        None,
        "country",
        "United Arab Emirates",
        "الإمارات العربية المتحدة",
        (51.5, 22.5, 56.6, 26.2),
    ),
    Territory("abu-dhabi", "uae", "emirate", "Abu Dhabi", "أبوظبي", (51.5, 22.5, 55.9, 25.2)),
    Territory("dubai", "uae", "emirate", "Dubai", "دبي", (54.8, 24.5, 56.3, 25.5)),
    Territory("sharjah", "uae", "emirate", "Sharjah", "الشارقة", (55.2, 24.8, 56.5, 25.7)),
    Territory("ajman", "uae", "emirate", "Ajman", "عجمان", (55.3, 24.7, 56.2, 25.5)),
    Territory(
        "umm-al-quwain", "uae", "emirate", "Umm Al Quwain", "أم القيوين", (55.5, 25.3, 55.9, 25.7)
    ),
    Territory(
        "ras-al-khaimah", "uae", "emirate", "Ras Al Khaimah", "رأس الخيمة", (55.5, 24.8, 56.5, 26.2)
    ),
    Territory("fujairah", "uae", "emirate", "Fujairah", "الفجيرة", (56.0, 24.9, 56.6, 25.7)),
    Territory(
        "al-reem-island",
        "abu-dhabi",
        "area",
        "Al Reem Island",
        "جزيرة الريم",
        (54.385, 24.465, 54.445, 24.530),
    ),
)
TERRITORY_BY_ID = {territory.id: territory for territory in TERRITORIES}
