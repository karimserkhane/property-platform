"""A rebuild must cover every reviewed area without clearing any existing table."""

from types import SimpleNamespace

import pytest

from property_platform_ingestion.registry import TERRITORIES


@pytest.mark.parametrize("territory", [None, "al-maryah-island"])
def test_optional_geography_rebuild_keeps_the_requested_scope(monkeypatch, territory):
    from property_platform_ingestion import flows, project_bootstrap

    collected = []

    def collect(kind, territory, **parameters):
        collected.append((territory, parameters.get("layer", kind)))

    monkeypatch.setattr(project_bootstrap, "prepare_catalogue", lambda actor: None)
    monkeypatch.setattr(project_bootstrap, "index_project_archive", lambda: {})
    project_scopes = []
    monkeypatch.setattr(
        project_bootstrap, "project_registry", lambda scope: project_scopes.append(scope) or []
    )
    monkeypatch.setattr(
        project_bootstrap, "get_run_logger", lambda: SimpleNamespace(info=lambda *args: None)
    )
    for kind in ("parcels", "sdi_parcels", "references", "map_layer"):
        monkeypatch.setattr(
            flows,
            kind,
            lambda *, territory, kind=kind, **parameters: collect(kind, territory, **parameters),
        )

    result = project_bootstrap.rebuild_projects.fn(
        mode="live", include_geography=True, include_catalogues=False, territory=territory
    )

    assert set(collected) == {
        (territory, layer)
        for territory in ((territory,) if territory else TERRITORIES)
        for layer in (
            "parcels",
            "sdi_parcels",
            "district",
            "community",
            "street",
            "osm",
            "references",
        )
    }
    expected_count = 7 if territory else 21
    assert len(collected) == expected_count
    assert len(result["geography_layers"]) == expected_count
    assert project_scopes == [territory]
    assert result["missing_or_failed"] == []
