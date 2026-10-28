"""Agency observations and zero-geography ingestion on real PostGIS."""

import base64
import hashlib
import json
import os
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Project source reconciliation requires PostGIS", allow_module_level=True)

from property_platform.modules.catalog.models import Place  # noqa: E402
from property_platform.modules.evidence.models import Capture, ProjectSnapshot  # noqa: E402
from property_platform.modules.evidence.projects.project_import import import_project_details  # noqa: E402
from property_platform.modules.evidence.projects.project_protocol import project_registry  # noqa: E402
from property_platform.modules.evidence.projects.project_queries import project_detail  # noqa: E402

# Agency, Aldar and relation fixtures use sites whose rights withhold them (A19); their
# replay mechanics remain tested here, what rights hide is in test_source_rights_postgis.py.
pytestmark = [
    pytest.mark.postgis,
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("unrestricted_sources"),
]


def test_a_long_project_and_source_identity_is_audited_without_truncation():
    from property_platform.modules.evidence.models import IngestionExecution
    from property_platform.modules.evidence.rebuild.orchestration import execute_import

    slug = "bab-al-qasr-beach-resort-residence-77"
    project = project_registry("al-reem-island:" + slug)[0]
    source = next(s for s in project["sources"] if s["parser"] == "psi_project_v1")
    scope = "al-reem-island:" + slug + ":" + hashlib.sha256(source["url"].encode()).hexdigest()
    assert len(scope) > 100
    result = execute_import(
        operation="project_details",
        scope=scope,
        execution_key="b" * 64,
        actor="test",
        prefect_flow_run_id=uuid.uuid4(),
        receipt=[agency_receipt(project, source)],
    )
    assert result["status"] == "succeeded"
    assert IngestionExecution.objects.get().scope == scope


def agency_receipt(project, source, *, lat=24.5003, lon=54.394):
    data = {
        "propertyId": int(source["record_id"]),
        "propertyName": source["heading_aliases"][0],
        "community": {
            "al-reem-island": "Al Reem Island",
            "saadiyat-island": "Saadiyat Island",
            "al-maryah-island": "Al Maryah Island",
        }[project["territory_id"]],
        "city": "Abu Dhabi",
        "developerName": source["developer_aliases"][0],
        "latitude": lat,
        "longitude": lon,
        "handoverDate": "2027-06-30",
        "unitTypes": ["Apartment"],
        "availableBedrooms": [1, 2],
    }
    text = '6:["$","$L27",null,{"data":' + json.dumps(data) + "}]"
    payload = (
        "<html><script>self.__next_f.push(" + json.dumps([1, text]) + ")</script></html>"
    ).encode()
    now = timezone.now().isoformat()
    return {
        "url": source["url"],
        "payload": base64.b64encode(payload).decode(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "http_status": 200,
        "fetched_started_at": now,
        "fetched_at": now,
    }


def ingest_renad(**coordinates):
    project = project_registry("al-reem-island:renad-tower")[0]
    source = next(s for s in project["sources"] if s["parser"] == "psi_project_v1")
    scope = "al-reem-island:renad-tower:" + hashlib.sha256(source["url"].encode()).hexdigest()
    receipt = agency_receipt(project, source, **coordinates)
    return import_project_details([receipt], territory=scope, actor="source-review-test")


def test_maryah_broker_project_is_rebuilt_from_source_and_served_in_its_own_territory(client):
    from django.test import override_settings

    project = project_registry("al-maryah-island:al-maryah-vista-2")[0]
    source = next(s for s in project["sources"] if s["parser"] == "psi_project_v1")
    scope = (
        "al-maryah-island:"
        + project["slug"]
        + ":"
        + hashlib.sha256(source["url"].encode()).hexdigest()
    )
    result = import_project_details(
        [agency_receipt(project, source, lat=24.4934, lon=54.3881)],
        territory=scope,
        actor="maryah-rebuild-test",
    )
    assert result["projects"] == result["locations"] == 1
    snapshot = ProjectSnapshot.objects.select_related("capture").get()
    assert snapshot.ingested_at >= snapshot.capture.fetched_at
    assert snapshot.source_kind == "broker"
    assert project_detail(project["slug"])["territory"] == "al-maryah-island"
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        maryah = client.get("/api/v1/preview/projects", {"territory": "al-maryah-island"})
        assert maryah.status_code == 200
        assert [row["slug"] for row in maryah.json()["items"]] == [project["slug"]]
        reem = client.get("/api/v1/preview/projects", {"territory": "al-reem-island"})
        assert reem.status_code == 200 and reem.json()["items"] == []


def test_agency_import_from_empty_catalogue_keeps_its_provenance_and_unverified_pin():
    assert Place.objects.count() == 0
    result = ingest_renad()
    assert result["projects"] == result["locations"] == 1
    snapshot = ProjectSnapshot.objects.select_related("capture").get()
    assert snapshot.source_kind == "broker"
    assert snapshot.source_name == "Property Shop Investment (PSI)"
    assert snapshot.ingested_at >= snapshot.capture.fetched_at
    data = project_detail("renad-tower")
    assert data["handover"]["source"]["kind"] == "broker"
    assert data["sources"][0]["name"] == "Property Shop Investment (PSI)"
    assert data["map_locations"][0]["source"]["kind"] == "broker"
    assert data["map_locations"][0]["method"] == "broker_point"
    assert data["map_locations"][0]["precision"] == "point"
    assert data["map_locations"][0]["source"]["name"] == "Property Shop Investment (PSI)"
    assert data["map_locations"][0]["geometry"]["coordinates"] == [54.394, 24.5003]


def test_reused_island_point_does_not_block_facts_or_invent_a_project_location():
    result = ingest_renad(lat=24.4942437, lon=54.4068603)
    assert result["projects"] == 1 and result["locations"] == 0
    assert project_detail("renad-tower")["map_locations"] == []


def test_older_developer_fact_wins_over_newer_agency_fact_without_hiding_missing_fields():
    ingest_renad()
    agency = ProjectSnapshot.objects.select_related("capture").get()
    proof = agency.capture
    proof.pk = None
    proof.url = "https://tigerproperties.ae/renad-tower/"
    proof.fetched_at -= timedelta(days=2)
    proof.fetched_started_at = proof.fetched_at
    proof.save(force_insert=True)
    ProjectSnapshot.objects.create(
        project=agency.project,
        capture=proof,
        receipt_key="a" * 64,
        extractor_version="fixture",
        source_role="project",
        source_kind="developer",
        source_name="Tiger Properties",
        title="Renad Tower",
        actor="test",
        handover_precision="quarter",
        handover_year=2028,
        handover_quarter=1,
        handover_original="Q1 2028",
        handover_pointer="fixture:announced-handover",
    )
    data = project_detail("renad-tower")
    assert data["handover"]["year"] == 2028
    assert data["handover"]["source"]["kind"] == "developer"
    assert data["updated_at"] == Capture.objects.latest("fetched_at").fetched_at
    assert len(data["typologies"]) == 2  # Agency supplies an otherwise absent fact.


def test_replaying_older_source_recovers_evidence_without_rewinding_current_pin():
    ingest_renad(lat=24.5003, lon=54.394)
    project = project_registry("al-reem-island:renad-tower")[0]
    source = next(s for s in project["sources"] if s["parser"] == "psi_project_v1")
    old = agency_receipt(project, source, lat=24.501, lon=54.395)
    old["fetched_at"] = old["fetched_started_at"] = (timezone.now() - timedelta(days=2)).isoformat()
    scope = "al-reem-island:renad-tower:" + hashlib.sha256(source["url"].encode()).hexdigest()
    import_project_details([old], territory=scope, actor="archive-recovery-test")
    assert ProjectSnapshot.objects.count() == 2
    assert list(Place.objects.get(active=True).geometry.coords) == [54.394, 24.5003]
    assert Capture.objects.filter(url=source["url"]).count() == 2
    assert project_detail("renad-tower")["sources"][0][
        "retrieved_at"
    ] > timezone.datetime.fromisoformat(old["fetched_at"])


def test_authority_registered_count_and_legal_party_are_published_without_merging_brand():
    project = project_registry("saadiyat-island:sensi")[0]
    source = next(s for s in project["sources"] if s["parser"] == "adrec_project_v1")
    payload = json.dumps(
        {
            "Success": True,
            "Data": {
                "Result": {
                    "Id": 669,
                    "Name": source["heading_aliases"][0],
                    "ProjectNumber": source["registration_number"],
                    "MunicipalityId": 1000,
                    "DistrictId": 2540,
                    "DistrictEn": "Al Saadiyat Island",
                    "DeveloperName": source["developer_aliases"][0],
                    "ResidentialUnits": 89,
                    "UnitCount": 999,
                    "PropertyProjectUnits": [],
                }
            },
        }
    ).encode()
    now = timezone.now().isoformat()
    row = {
        "url": source["url"],
        "payload": base64.b64encode(payload).decode(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "http_status": 200,
        "fetched_at": now,
        "fetched_started_at": now,
    }
    scope = "saadiyat-island:sensi:" + hashlib.sha256(source["url"].encode()).hexdigest()
    import_project_details([row], territory=scope, actor="authority-review-test")
    data = project_detail("sensi")
    assert data["developer"]["name"] == "Reportage Properties"
    assert data["programme_total"]["value"] == 89
    assert data["programme_total"]["basis"] == "registered"
    assert data["programme_total"]["source"]["kind"] == "authority"
    assert data["sources"][0]["developer_name"].startswith("NOVA MIDDLE EAST")
    assert data["sources"][0]["developer_role"] == "registered"
    assert data["map_locations"] == []  # No coordinates means no invented island-centre pin.


def test_reviewed_wrong_media_references_are_withdrawn_even_on_idempotent_reimport():
    from property_platform.modules.evidence.models import ProjectMedia

    project = project_registry("al-reem-island:canal-residence")[0]
    source = project["sources"][0]
    payload = b"<html><title>by M</title><body><div>Project | Canal Residence</div></body></html>"
    now = timezone.now().isoformat()
    row = {
        "url": source["url"],
        "payload": base64.b64encode(payload).decode(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "http_status": 200,
        "fetched_at": now,
        "fetched_started_at": now,
    }
    scope = "al-reem-island:canal-residence:" + hashlib.sha256(source["url"].encode()).hexdigest()
    import_project_details([row], territory=scope, actor="test")
    snapshot = ProjectSnapshot.objects.get()
    legacy = ProjectMedia.objects.create(
        snapshot=snapshot,
        kind="document",
        role="brochure",
        title="Legacy wrong reference",
        mime_type="application/pdf",
        source_url=source["excluded_media_urls"][0],
        original_text="Legacy parsed link",
        evidence_pointer="fixture:legacy-parser",
    )
    assert import_project_details([row], territory=scope, actor="test-review")["reused"] == 1
    legacy.refresh_from_db()
    assert legacy.rights_status == "blocked"
    assert ProjectSnapshot.objects.count() == 1  # Proof survives; no destructive replacement.
    assert project_detail("canal-residence")["media"] == []


@pytest.mark.parametrize(
    ("target", "observed", "method"),
    [
        ("parcel", None, "cadastral_parcel"),
        ("building", "broker_project_coordinates", "building_footprint"),
        ("place", "authority_registered_project_coordinates", "authority_point"),
        ("place", "broker_project_coordinates", "broker_point"),
        ("place", "publisher_map", "publisher_point"),
        ("place", None, "declared_point"),
    ],
)
def test_location_method_follows_the_identity_and_never_upgrades_a_point(target, observed, method):
    from property_platform.modules.evidence.projects.project_queries import (
        LOCATION_PRECISION,
        location_method,
    )

    assert location_method(target, observed) == method
    assert LOCATION_PRECISION[method] == {"parcel": "boundary", "building": "footprint"}.get(
        target, "point"
    )
