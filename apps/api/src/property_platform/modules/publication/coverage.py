"""Explicit collection profiles: listing a territory does not activate its sources."""

from dataclasses import asdict, dataclass

from property_platform.modules.catalog.territories import (
    DEFAULT_TERRITORY_ID,
    TERRITORIES,
    TERRITORY_BY_ID,
)
from property_platform.modules.evidence.collection_profiles import collection_for
from property_platform.modules.evidence.maps.onwani import SOURCE_KEY
from property_platform.modules.evidence.maps.sdi_protocol import namespace as sdi_namespace
from property_platform.modules.evidence.source_rights import facts_allowed

# Agency pins keep a namespace of their own, per publisher (`project_locations.py`).
BROKER_PARSERS = {"psi_project_v1": "psi", "propertyfinder_project_v1": "propertyfinder"}


@dataclass(frozen=True)
class CoverageProfile:
    parcel_namespaces: tuple[str, ...]
    camera_bounds: tuple[float, float, float, float]
    focus_bounds: tuple[float, float, float, float] | None = None
    neighbourhood_bounds: tuple[float, float, float, float] | None = None
    reference_registry: str | None = None
    imagery_ids: tuple[str, ...] = ()
    member_territory_ids: tuple[str, ...] = ()


# Provider identities are retained; replacing them would create duplicate catalogue objects.
PROFILES = {
    "al-reem-island": CoverageProfile(
        (SOURCE_KEY, sdi_namespace("al-reem-island")),
        (54.388, 24.47, 54.429, 24.519),
        (54.389, 24.493, 54.404, 24.507),
        (54.392, 24.491, 54.408, 24.502),
        "project_sources.json",
        ("S2C_40RBN_20261004_0_L2A", "S2C_40RBN_20260629_0_L2A"),
    ),
    "saadiyat-island": CoverageProfile(
        (collection_for("saadiyat-island").parcel_namespace, sdi_namespace("saadiyat-island")),
        (54.386, 24.4886, 54.4812, 24.6019),
        (54.391, 24.524, 54.431, 24.553),
        (54.405, 24.534, 54.422, 24.548),
        "saadiyat_project_sources.json",
    ),
    "al-maryah-island": CoverageProfile(
        (collection_for("al-maryah-island").parcel_namespace, sdi_namespace("al-maryah-island")),
        (54.383, 24.488, 54.400, 24.517),
        (54.385, 24.490, 54.398, 24.515),
        (54.385, 24.490, 54.398, 24.515),
        "maryah_project_sources.json",
    ),
}


def combined_profile(member_ids):
    """Compose reviewed read scopes; this never activates an emirate-wide collector."""
    profiles = [PROFILES[key] for key in member_ids]
    return CoverageProfile(
        parcel_namespaces=tuple(
            dict.fromkeys(key for p in profiles for key in p.parcel_namespaces)
        ),
        camera_bounds=union_bounds(p.camera_bounds for p in profiles),
        imagery_ids=tuple(dict.fromkeys(key for p in profiles for key in p.imagery_ids)),
        member_territory_ids=tuple(member_ids),
    )


def union_bounds(bounds):
    rows = tuple(bounds)
    return (
        min(r[0] for r in rows),
        min(r[1] for r in rows),
        max(r[2] for r in rows),
        max(r[3] for r in rows),
    )


# Whole area means the explicitly mapped islands, not every official district.
PROFILES["abu-dhabi"] = combined_profile(tuple(PROFILES))


def profile_for(territory_id):
    return PROFILES.get(territory_id)


def member_territories(territory_id):
    profile = profile_for(territory_id)
    if profile is None:
        return ()
    return profile.member_territory_ids or (territory_id,)


def coverage_registry():
    from property_platform.modules.catalog.queries import parcel_counts

    namespaces = {key for profile in PROFILES.values() for key in profile.parcel_namespaces}
    counts = parcel_counts(namespaces)
    entries = []
    for territory in TERRITORIES:
        profile = profile_for(territory.id)
        count = sum(counts.get(key, 0) for key in profile.parcel_namespaces) if profile else 0
        entries.append(
            {
                **asdict(territory),
                "queryable": profile is not None,
                "parcel_count": count,
                "member_territory_ids": member_territories(territory.id),
                "collection_bounds": union_bounds(
                    TERRITORY_BY_ID[key].bounds for key in member_territories(territory.id)
                )
                if profile
                else None,
                "camera_bounds": profile.camera_bounds if profile else territory.bounds,
                "focus_bounds": profile.focus_bounds if profile else None,
                "neighbourhood_bounds": profile.neighbourhood_bounds if profile else None,
            }
        )
    return {"default_territory_id": DEFAULT_TERRITORY_ID, "territories": entries}


def navigation_registry():
    """Build-time public metadata; queryability describes a configured pilot, not live counts."""
    return {
        "default_territory_id": DEFAULT_TERRITORY_ID,
        "territories": [
            {**asdict(territory), "queryable": profile_for(territory.id) is not None}
            for territory in TERRITORIES
        ],
    }


def reference_source_keys(profile, *, withheld=False):
    """Namespaces of reviewed references, or of those whose facts are withheld (A19)."""
    import hashlib
    import json
    from pathlib import Path

    if profile.member_territory_ids:
        return tuple(
            dict.fromkeys(
                key
                for member in profile.member_territory_ids
                for key in reference_source_keys(PROFILES[member], withheld=withheld)
            )
        )
    if not profile.reference_registry:
        return ()
    # Paths belong to trusted deployment configuration, never to query parameters.
    registry = Path(__file__).parent.parent / "evidence" / profile.reference_registry
    return tuple(
        "research:" + hashlib.sha256(row["url"].encode()).hexdigest()[:40]
        for row in json.loads(registry.read_text(encoding="utf-8"))
        if facts_allowed(row["url"]) != withheld
    )


def map_source_namespaces(territory_id):
    from property_platform.modules.evidence.projects.project_protocol import project_registry

    members = member_territories(territory_id)
    return (
        tuple(
            dict.fromkeys(
                collection_for(member).map_namespace(layer)
                for member in members
                for layer in ("district", "community", "street", "osm", "overture")
            )
        )
        + reference_source_keys(profile_for(territory_id))
        + tuple(
            namespace
            for project in project_registry()
            if project["territory_id"] in members
            for namespace in (
                f"project:{project['slug']}",
                *_broker_namespaces(project, withheld=False),
            )
        )
    )


def _broker_namespaces(project, *, withheld):
    return tuple(
        dict.fromkeys(
            f"project:{project['slug']}:broker:{BROKER_PARSERS[source['parser']]}"
            for source in project["sources"]
            if source["parser"] in BROKER_PARSERS and facts_allowed(source["url"]) != withheld
        )
    )


def withheld_place_namespaces():
    """Map identities declared only by sites whose facts are withheld (A19)."""
    from property_platform.modules.evidence.projects.project_protocol import project_registry

    return tuple(
        dict.fromkeys(
            (
                *(
                    namespace
                    for project in project_registry()
                    for namespace in _broker_namespaces(project, withheld=True)
                ),
                *(
                    key
                    for profile in PROFILES.values()
                    if not profile.member_territory_ids
                    for key in reference_source_keys(profile, withheld=True)
                ),
            )
        )
    )
