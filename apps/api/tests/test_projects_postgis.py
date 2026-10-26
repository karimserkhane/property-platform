import copy
import os
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Project identity and evidence require real PostGIS", allow_module_level=True)

from django.contrib.gis.geos import MultiPolygon, Polygon  # noqa: E402
from django.db import IntegrityError, connection, transaction  # noqa: E402
from test_property_protocol import receipt  # noqa: E402

from property_platform.modules.catalog.models import Building, Developer, Project  # noqa: E402
from property_platform.modules.evidence import project_protocol  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    IngestionRun,
    ProjectIdentityLink,
    ProjectMedia,
    ProjectSnapshot,
)
from property_platform.modules.evidence.project_import import (  # noqa: E402
    import_project_details,
    interpretation_sha256,
    registry_sha256,
    revoke_project_link,
)
from property_platform.modules.evidence.project_queries import (  # noqa: E402
    project_detail,
    project_directory,
    project_location_gaps,
    project_locations,
    project_references,
)

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


@pytest.fixture
def project_input(monkeypatch):
    original_registry = project_protocol.project_registry

    def first_party_registry(scope=None):
        rows = original_registry(scope)
        for row in rows:
            row["sources"] = [
                s
                for s in row["sources"]
                if s["parser"] not in {"psi_project_v1", "adrec_project_v1"}
            ]
        return rows

    monkeypatch.setattr(project_protocol, "project_registry", first_party_registry)
    definition = project_protocol.project_registry("saadiyat-island")[0]
    for link in definition["identity_links"]:
        Building.objects.create(
            source_namespace=link["namespace"],
            source_record_id=link["record_id"],
            name="Provider building",
            kind="residential",
            geometry=MultiPolygon(Polygon.from_bbox((54.42, 24.54, 54.421, 24.541)), srid=4326),
        )
    rows = [
        receipt(source["url"], b"<html>Source evidence Terms</html>")
        for source in definition["sources"]
    ]
    parsed = {
        "title": definition["name"],
        "parser_version": "fixture-extractor-v1",
        "summary": "",
        "handover": {
            "precision": "quarter",
            "year": 2029,
            "quarter": 2,
            "original_text": "Q2 2029",
            "evidence_pointer": "Handover",
        },
        "total_units": 230,
        "total_units_original": "230 residential units",
        "total_units_pointer": "Programme",
        "typologies": [
            {
                "property_type": "studio",
                "bedrooms": 0,
                "original_text": "Studio",
                "evidence_pointer": "Unit types",
            }
        ],
        "amenities": [
            {
                "code": "swimming-pool",
                "label": "Swimming pool",
                "original_text": "Swimming pool",
                "evidence_pointer": "Amenities",
            }
        ],
        "media": [
            {
                "kind": "video",
                "role": "tour",
                "title": "Official video",
                "mime_type": "text/html",
                "source_url": "https://vimeo.com/1038853770",
                "original_text": "Official video",
                "evidence_pointer": "Video link",
                "rights_status": "reference_only",
            }
        ],
    }

    def extract(project, source, received):
        return None if source["role"] == "terms" else copy.deepcopy(parsed)

    with patch.object(project_protocol, "extract_project_source", side_effect=extract):
        yield definition, rows, parsed


def ingest(rows):
    return import_project_details(
        rows, territory="saadiyat-island:park-view", actor="test-reviewer"
    )


def test_project_import_is_typed_idempotent_and_retains_provider_identities(project_input, client):
    definition, rows, _ = project_input
    first, second = ingest(rows), ingest(rows)
    assert first["snapshots"] == 1 and second["snapshots"] == 0 and second["reused"] == 1
    assert (
        Project.objects.count() == Developer.objects.count() == ProjectSnapshot.objects.count() == 1
    )
    assert ProjectIdentityLink.objects.count() == 3
    assert Capture.objects.count() == 2  # source + captured terms, no binary rehosting
    # Each reading keeps the exact registry entry and extraction code that produced it.
    snapshot = ProjectSnapshot.objects.get()
    registered = next(
        row
        for row in project_protocol.project_registry("saadiyat-island:park-view")
        if row["slug"] == definition["slug"]
    )
    assert snapshot.registry_sha256 == registry_sha256(registered)
    assert snapshot.extractor_sha256 == interpretation_sha256()
    assert set(Building.objects.values_list("name", flat=True)) == {"Provider building"}
    with CaptureQueriesContext(connection) as queries:
        data = project_detail(definition["slug"])
    # B04: latest declared progress. B05: exclusions, cited readings, official links.
    # B07: satellite measurements. C01: reviewed sales labels.
    assert len(queries) <= 13
    assert all('"payload"' not in query["sql"] for query in queries)
    assert data["handover"]["precision"] == "quarter"
    assert data["handover"]["day"] is None and data["handover"]["month"] is None
    assert data["programme_total"]["value"] == 230
    assert len(data["map_locations"]) == 3
    assert all(location["target"] == "building" for location in data["map_locations"])
    assert {(row["method"], row["precision"]) for row in data["map_locations"]} == {
        ("building_footprint", "footprint")
    }
    assert data["typologies"][0]["bedrooms"] == 0
    assert data["media"][0]["delivery_url"] is None
    assert data["media"][0]["rights_status"] == "reference_only"
    assert not {"actor", "receipt_key", "payload", "storage_key"} & data.keys()
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get(f"/api/v1/preview/projects/{definition['slug']}")
        assert response.status_code == 200
        assert response.json()["developer"]["key"] == "bloom-holding"
        assert client.get("/api/v1/preview/projects/not-registered").status_code == 404
    with override_settings(DEBUG=False, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        assert client.get(f"/api/v1/preview/projects/{definition['slug']}").status_code == 403


@pytest.mark.parametrize(("reviewed_on", "links"), [("2099-01-01", 3), ("2026-01-01", 0)])
def test_a_dated_link_cites_its_page_as_of_its_review_day(
    project_input, monkeypatch, reviewed_on, links
):
    definition, rows, _ = project_input
    registry = project_protocol.project_registry

    def dated(scope=None):
        result = registry(scope)
        for row in result:
            if row["slug"] != definition["slug"]:
                continue
            page = next(source["url"] for source in row["sources"] if source["role"] != "terms")
            for link in row["identity_links"]:
                link.update(reviewed_on=reviewed_on, source_url=page)
        return result

    monkeypatch.setattr(project_protocol, "project_registry", dated)
    ingest(rows)
    # No capture of the page by the review day yet: the link waits, nothing is invented.
    assert ProjectIdentityLink.objects.count() == links
    if links:
        first = ProjectIdentityLink.objects.first().capture.fetched_at
        ingest([receipt(row["url"], b"<html>Later page Terms</html>") for row in rows])
        # Whatever the import order, the latest capture by the review day is cited.
        assert ProjectIdentityLink.objects.count() == links
        assert all(row.capture.fetched_at > first for row in ProjectIdentityLink.objects.all())


def test_revoked_project_link_stays_revoked_after_fresh_acquisition(project_input):
    _, rows, _ = project_input
    ingest(rows)
    link = ProjectIdentityLink.objects.order_by("id").first()
    revoke_project_link(link.id, actor="reviewer", reason="Association withdrawn")
    assert str(link.building_id) not in project_references("building", [link.building_id])
    fresh = [receipt(row["url"], b"<html>New source evidence Terms</html>") for row in rows]
    ingest(fresh)
    link.refresh_from_db()
    assert link.active is False and link.revoked_by == "reviewer"
    assert ProjectIdentityLink.objects.count() == 3
    assert ProjectSnapshot.objects.count() == 2


def test_map_locations_exclude_inactive_revoked_and_outside_identities(project_input):
    _, rows, _ = project_input
    ingest(rows)
    project = Project.objects.select_related("developer").get(slug="park-view")
    assert project_location_gaps() == []
    links = list(ProjectIdentityLink.objects.select_related("building").order_by("id"))
    links[0].building.active = False
    links[0].building.save(update_fields=["active"])
    revoke_project_link(links[1].id, actor="reviewer", reason="Unconfirmed membership")
    assert len(project_locations(project)) == 1
    links[2].building.geometry = MultiPolygon(Polygon.from_bbox((55, 25, 55.01, 25.01)), srid=4326)
    links[2].building.save(update_fields=["geometry"])
    assert project_locations(project) == []
    assert project_directory()["items"][0]["has_map_identity"] is False
    gaps = project_location_gaps("saadiyat-island")
    assert [(row["slug"], row["priority"]) for row in gaps] == [("park-view", 2)]
    assert project_location_gaps("al-reem-island") == []


def test_excluded_source_cannot_advertise_project_or_map_identity(project_input):
    from property_platform.modules.evidence.models import HistoryExclusion

    _, rows, _ = project_input
    ingest(rows)
    old = ProjectSnapshot.objects.get()
    # A separately reviewed link cannot publish a dossier with no accepted facts.
    ProjectIdentityLink.objects.update(capture=old.terms_capture)
    HistoryExclusion.objects.create(
        dataset="project:park-view",
        record_key=old.capture.url,
        capture=old.capture,
        actor="reviewer",
        reason="Source identity was incorrect",
    )
    assert project_detail("park-view") is None
    assert project_directory()["total"] == 0
    assert project_references("building", list(Building.objects.values_list("pk", flat=True))) == {}
    assert ProjectSnapshot.objects.count() == 1  # Preserved, not deleted.


@pytest.mark.parametrize("field_only", [False, True])
def test_excluded_media_source_does_not_mask_accepted_reference(project_input, field_only):
    from property_platform.modules.evidence.models import HistoryExclusion

    _, rows, _ = project_input
    ingest(rows)
    accepted = ProjectSnapshot.objects.get()
    ingest([receipt(row["url"], b"<html>Another observation</html>") for row in rows])
    newer = ProjectSnapshot.objects.latest("id")
    newer.capture.url = "https://bloomholding.com/rejected-source"
    newer.capture.save(update_fields=["url"])
    ProjectMedia.objects.filter(snapshot=newer).update(title="Incorrect attribution")
    HistoryExclusion.objects.create(
        dataset="project:park-view",
        record_key=newer.capture.url + ("#media" if field_only else ""),
        capture=newer.capture,
        actor="reviewer",
        reason="Media source attribution withdrawn",
    )
    result = project_detail("park-view")
    assert len(result["media"]) == 1
    assert result["media"][0]["source"]["url"] == accepted.capture.url
    assert result["media"][0]["title"] == "Official video"


def test_source_position_is_audited_idempotent_and_respects_revocation(project_input):
    from property_platform.modules.evidence.models import MapObservation
    from property_platform.modules.evidence.project_locations import materialize_project_position

    _, rows, _ = project_input
    ingest(rows)
    snapshot = ProjectSnapshot.objects.select_related("project", "capture__run__source").get()
    marker = {"name": "Park View", "lat": 24.524, "lon": 54.433, "method": "publisher_map"}
    for _ in range(2):
        assert materialize_project_position(
            snapshot.project, snapshot.capture, marker, actor="test"
        )
    link = ProjectIdentityLink.objects.get(project=snapshot.project, place__isnull=False)
    assert (
        MapObservation.objects.get(place=link.place).raw_attributes["location_status"]
        == "declared_unverified"
    )
    revoke_project_link(link.id, actor="reviewer", reason="Position rejected")
    assert not materialize_project_position(
        snapshot.project, snapshot.capture, marker, actor="test"
    )
    assert ProjectIdentityLink.objects.filter(place=link.place).count() == 1


def test_changed_developer_identity_rolls_back_complete_batch(project_input):
    _, rows, _ = project_input
    ingest(rows)
    Developer.objects.update(name="Manually reviewed different name")
    fresh = [receipt(row["url"], b"<html>Fresh source evidence Terms</html>") for row in rows]
    with pytest.raises(ValueError, match="Developer identity changed"):
        ingest(fresh)
    assert ProjectSnapshot.objects.count() == IngestionRun.objects.count() == 1


def test_camera_position_review_preserves_history_and_cannot_restore_rejected_pin(project_input):
    from property_platform.modules.evidence.models import MapObservation
    from property_platform.modules.evidence.project_locations import (
        materialize_project_position,
        withdraw_camera_positions,
    )

    _, rows, _ = project_input
    ingest(rows)
    snapshot = ProjectSnapshot.objects.select_related("project", "capture__run__source").get()
    marker = {
        "name": "Park View",
        "lat": 24.524,
        "lon": 54.433,
        "method": "publisher_map_viewpoint",
    }
    materialize_project_position(snapshot.project, snapshot.capture, marker, actor="test")
    link = ProjectIdentityLink.objects.get(place__isnull=False)
    assert withdraw_camera_positions(actor="reviewer") == [str(link.place_id)]
    link.refresh_from_db()
    link.place.refresh_from_db()
    assert not link.active and not link.place.active
    correction = MapObservation.objects.get(place=link.place, action="retired")
    assert correction.capture.parent_capture_id == snapshot.capture_id
    assert correction.capture.fetched_at == snapshot.capture.fetched_at
    assert ProjectSnapshot.objects.count() == 1
    assert withdraw_camera_positions(actor="reviewer") == []
    assert not materialize_project_position(
        snapshot.project, snapshot.capture, marker, actor="test"
    )


def test_source_extraction_failure_has_no_partial_database_writes(project_input):
    _, rows, _ = project_input
    with patch.object(
        project_protocol, "extract_project_source", side_effect=ValueError("Changed page")
    ):
        with pytest.raises(ValueError, match="Changed page"):
            ingest(rows)
    assert Project.objects.count() == IngestionRun.objects.count() == Capture.objects.count() == 0


def test_sql_rolls_back_facts_if_media_cannot_be_saved(project_input):
    _, rows, _ = project_input
    with patch.object(ProjectMedia.objects, "create", side_effect=ValueError("Invalid media")):
        with pytest.raises(ValueError, match="Invalid media"):
            ingest(rows)
    assert (
        Project.objects.count() == Capture.objects.count() == ProjectSnapshot.objects.count() == 0
    )


@pytest.mark.parametrize(
    "values",
    [
        {"handover_year": None},
        {"handover_quarter": None},
        {"handover_quarter": 5},
        {"handover_month": 6},
        {"handover_day": 1},
    ],
)
def test_handover_constraints_cannot_invent_precision_or_omit_year(project_input, values):
    _, rows, _ = project_input
    ingest(rows)
    with pytest.raises(IntegrityError), transaction.atomic():
        ProjectSnapshot.objects.update(**values)


def test_media_redistribution_requires_separate_review_and_binary_capture(project_input):
    _, rows, _ = project_input
    ingest(rows)
    with pytest.raises(IntegrityError), transaction.atomic():
        ProjectMedia.objects.update(rights_status="approved")
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        assert project_detail("park-view")["media"][0]["delivery_url"] is None


def test_missing_new_source_fields_preserves_other_source_evidence(project_input):
    _, rows, parsed = project_input
    ingest(rows)
    old = ProjectSnapshot.objects.first()
    # A second independently captured source carries no delivery claim.
    parsed["handover"] = None
    fresh = [receipt(row["url"], b"<html>Offer source Terms</html>") for row in rows]
    ingest(fresh)
    newer = ProjectSnapshot.objects.latest("id")
    newer.capture.url = "https://bloomholding.com/other-project-source"
    newer.capture.save(update_fields=["url"])
    data = project_detail("park-view")
    assert data["handover"]["original_text"] == old.handover_original
    assert data["handover"]["source"]["url"] == rows[0]["url"]


def test_same_source_losing_fields_recovers_the_last_known_values(project_input):
    _, rows, parsed = project_input
    ingest(rows)
    old = ProjectSnapshot.objects.get()
    parsed.update(
        handover=None,
        total_units=None,
        total_units_original="",
        total_units_pointer="",
        typologies=[],
        amenities=[],
    )
    ingest([receipt(row["url"], b"<html>Changed page with missing records</html>") for row in rows])
    result = project_detail("park-view")
    assert ProjectSnapshot.objects.count() == 2
    assert result["handover"]["year"] == old.handover_year
    assert result["programme_total"]["value"] == old.total_units
    assert result["typologies"] and result["amenities"]
    assert result["handover"]["source"]["historical"] is True
    assert result["handover"]["source"]["retrieved_at"] == old.capture.fetched_at


def test_confirmed_claim_withdrawal_and_blocked_media_are_not_revived(project_input):
    from property_platform.modules.evidence.models import HistoryExclusion

    _, rows, parsed = project_input
    ingest(rows)
    old = ProjectSnapshot.objects.get()
    HistoryExclusion.objects.create(
        dataset="project:park-view",
        record_key=f"{old.capture.url}#handover",
        capture=old.capture,
        actor="reviewer",
        reason="Publisher confirmed this delivery claim is withdrawn",
    )
    ingest([receipt(row["url"], b"<html>Media withdrawn by publisher</html>") for row in rows])
    ProjectMedia.objects.filter(snapshot=ProjectSnapshot.objects.latest("id")).update(
        rights_status="blocked"
    )
    result = project_detail("park-view")
    assert result["handover"] is None and result["media"] == []


def test_partial_project_lists_retain_missing_individual_records(project_input):
    _, rows, parsed = project_input
    parsed["typologies"].append(
        {
            "property_type": "apartment",
            "bedrooms": 1,
            "original_text": "One bedroom",
            "evidence_pointer": "Types",
        }
    )
    parsed["amenities"].append(
        {"code": "gym", "label": "Gym", "original_text": "Gym", "evidence_pointer": "Amenities"}
    )
    ingest(rows)
    parsed["typologies"] = parsed["typologies"][1:]
    parsed["amenities"] = parsed["amenities"][1:]
    ingest([receipt(row["url"], b"<html>Partial list update</html>") for row in rows])
    result = project_detail("park-view")
    assert {row["property_type"] for row in result["typologies"]} == {"studio", "apartment"}
    assert {row["code"] for row in result["amenities"]} == {"swimming-pool", "gym"}
    assert next(row for row in result["typologies"] if row["property_type"] == "studio")["source"][
        "historical"
    ]
