"""Published-state comparison of the rebuild check; portable checks without a database."""

import copy
import re
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from property_platform.modules.evidence.projects.project_import import (
    interpretation_sha256,
    registry_sha256,
)
from property_platform.modules.evidence.rebuild_published import canonical, compare_published

SOURCE = {
    "url": "https://example.com/tower",
    "retrieved_at": datetime(2026, 10, 1, tzinfo=UTC),
    "ingested_at": datetime(2026, 10, 24, tzinfo=UTC),
}


def dossier(**changes):
    return {
        "id": uuid4(),
        "slug": "tower",
        "summary": "Two towers",
        "developer": {"id": uuid4(), "key": "aldar-properties"},
        "typologies": [
            {"property_type": "studio", "bedrooms": 0, "source": SOURCE},
            {"property_type": "apartment", "bedrooms": 1, "source": SOURCE},
        ],
        "media": [{"id": uuid4(), "delivery_url": None, "source": SOURCE}],
        "map_locations": [
            {
                "id": uuid4(),
                "geometry": {"type": "LineString", "coordinates": [[54.4, 24.5], [54.3, 24.4]]},
            }
        ],
    } | changes


def state(*dossiers, links=(), decisions=None):
    return {
        "version": 1,
        "projects": {item["slug"]: canonical(item) for item in dossiers},
        "identity_links": list(links),
        "decisions": decisions or {},
    }


def link(project="tower", record_id="1"):
    return {
        "project": project,
        "target": "building",
        "namespace": "osm:test",
        "record_id": record_id,
        "reason": "Reviewed",
    }


def test_interpretation_identity_is_exact_and_ignores_key_order():
    assert registry_sha256({"slug": "a", "sources": [1]}) == registry_sha256(
        {"sources": [1], "slug": "a"}
    )
    assert registry_sha256({"slug": "a"}) != registry_sha256({"slug": "b"})
    assert re.fullmatch(r"[a-f0-9]{64}", interpretation_sha256())


def test_canonical_drops_database_identities_and_ingestion_clocks_only():
    first, second = dossier(), dossier()
    second["typologies"].reverse()
    assert canonical(first) == canonical(second)
    value = canonical(first)
    assert "id" not in value and "id" not in value["developer"]
    assert "ingested_at" not in value["typologies"][0]["source"]
    assert value["typologies"][0]["source"]["retrieved_at"] == "2026-10-01T00:00:00+00:00"
    # Delivery is a published fact; a private storage location is not.
    assert value["media"][0] == {"delivered": False, "source": canonical(SOURCE)}
    # Coordinates keep their order: a reversed line is another geometry.
    assert value["map_locations"][0]["geometry"]["coordinates"] == [[54.4, 24.5], [54.3, 24.4]]
    reversed_line = dossier()
    reversed_line["map_locations"][0]["geometry"]["coordinates"].reverse()
    assert canonical(reversed_line) != value


def test_canonical_register_values_are_exact_json_text():
    # B05 verification facts are decimals; the manifest is JSON and keeps their text.
    value = canonical({"verification": [{"progress_percent": Decimal("42.50")}, {"x": 1}]})
    assert value["verification"][0] == {"progress_percent": "42.50"}


def test_identical_published_state_passes():
    expected = state(dossier(), links=[link()])
    result = compare_published(expected, copy.deepcopy(expected))
    assert result["ok"] and result["identical_projects"] == 1 and result["blocking"] == 0


def test_a_changed_or_missing_published_fact_blocks():
    expected = state(dossier(), dossier(slug="other"), links=[link()])
    actual = state(
        dossier(summary="One tower", typologies=dossier()["typologies"][:1]), links=[link()]
    )
    result = compare_published(expected, actual)
    assert not result["ok"] and result["blocking"] == 3
    other, tower = result["different_projects"]
    assert other == {
        "slug": "other",
        "differences": [{"path": "", "status": "missing", "requires_backup": []}],
        "difference_count": 1,
        "blocking": 1,
    }
    paths = {item["path"]: item for item in tower["differences"]}
    assert paths[".summary"]["expected"] == '"Two towers"'
    assert paths[".typologies"]["counts"] == {"missing": 1, "added": 0}


def test_a_missing_identity_link_blocks():
    result = compare_published(state(dossier(), links=[link()]), state(dossier()))
    assert not result["ok"]
    assert result["identity_links"]["missing_blocking"] == 1


def test_only_an_operator_decision_kept_by_backups_explains_its_own_fields():
    decisions = {"tower": ["link_revocation"]}
    expected = state(dossier(map_locations=[]), links=[], decisions=decisions)
    # A fresh rebuild recreates a link the owner revoked: only A03 restores that decision.
    actual = state(dossier(), links=[link()])
    result = compare_published(expected, actual)
    assert result["ok"] and result["requires_backup"] == ["tower"]
    assert result["identity_links"]["added"] and not result["identity_links"]["added_blocking"]
    # The same decision never explains another published field…
    actual = state(dossier(summary="Changed"), links=[link()])
    result = compare_published(expected, actual)
    assert not result["ok"] and result["blocking"] == 1
    # …nor a kept position whose evidence changed: a revocation only withdraws.
    cited = dossier()
    cited["map_locations"][0]["source"] = SOURCE
    expected = state(cited, links=[link()], decisions=decisions)
    actual = state(dossier(), links=[link()])
    result = compare_published(expected, actual)
    assert not result["ok"] and result["different_projects"][0]["blocking"] == 1
