"""Every data row reads the reviewed rights of the site it came from, in SQL (A23)."""

import os

import pytest
from django.db import connection

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Data rights require real PostGIS", allow_module_level=True)

from test_source_rights_postgis import (  # noqa: E402
    ALDAR_PAGE,
    DEVELOPER_PAGE,
    PSI_PAGE,
    capture,
    project,
    snapshot,
)

from property_platform.modules.catalog.models import Developer  # noqa: E402
from property_platform.modules.evidence import source_rights  # noqa: E402
from property_platform.modules.evidence.history.pipeline_inventory import (  # noqa: E402
    RIGHTS_EXEMPT,
    inventory,
)
from property_platform.modules.evidence.models import (  # noqa: E402
    ProjectSnapshot,
    SourceRightsEnforcement,
)
from property_platform.modules.evidence.source_rights_import import (  # noqa: E402
    apply_source_rights,
)

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

ACTOR = "data-rights-test"
EXTRACT = "https://download.geofabrik.de/asia/gcc-states-261019.osm.pbf"
METHOD = "https://valhalla.github.io/valhalla/api/isochrone/api-reference/"
INTERNAL = "https://property-platform.invalid/internal/history-inventory"


def rights(dataset, **where):
    filters = "".join(f" AND {column} = %s" for column in where)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM evidence.data_rights WHERE dataset = %s" + filters + " ORDER BY row_id",
            [dataset, *where.values()],
        )
        columns = [column.name for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def mirrored(enforce_rights, *, publication=False):
    enforce_rights(collection=False, publication=publication)
    apply_source_rights(actor=ACTOR)


def test_each_row_reads_the_reviewed_rights_of_its_site(enforce_rights):
    renad = project("renad-tower")
    psi = snapshot(renad, PSI_PAGE)
    developer = snapshot(renad, DEVELOPER_PAGE)
    mirrored(enforce_rights)
    rows = {row["capture_id"]: row for row in rights("evidence.project_snapshot")}
    withheld = rows[psi.capture_id]
    assert (withheld["licence"], withheld["publication"], withheld["collection"]) == (
        "proprietary",
        "none",
        "forbidden",
    )
    assert withheld["reviewed_host"] == "psinv.net"
    assert withheld["terms_url"] == "https://psinv.net/en/terms"
    assert withheld["qualified"]
    # Collected and shown although the terms forbid it, as Karim decided (A22).
    assert withheld["collected_against_terms"]
    assert withheld["shown_beyond_terms"]
    listed = rows[developer.capture_id]
    assert (listed["licence"], listed["publication"], listed["qualified"]) == (
        "unknown",
        "facts",
        False,
    )
    assert not listed["collected_against_terms"] and not listed["shown_beyond_terms"]
    # A catalogue row has one rights row per capture it was read from.
    assert {row["capture_id"] for row in rights("real_estate.project")} == set(rows)


def test_a_host_no_review_lists_stays_unqualified(enforce_rights):
    unlisted = capture("https://news.example.org/abu-dhabi/towers")
    mirrored(enforce_rights)
    [row] = rights("evidence.capture", capture_id=unlisted.id)
    assert row["source_rights_id"] is None and row["reviewed_host"] is None
    assert (row["licence"], row["collection"], row["publication"]) == (
        "unknown",
        "allowed",
        "facts",
    )
    assert row["source_host"] == "news.example.org"
    assert not row["qualified"]


def test_a_local_computation_inherits_the_rights_of_its_source_capture(enforce_rights):
    extract = capture(EXTRACT)
    computed = capture(METHOD)
    computed.parent_capture = extract
    computed.save(update_fields=["parent_capture"])
    inventory_capture = capture(INTERNAL)
    mirrored(enforce_rights)
    [row] = rights("evidence.capture", capture_id=computed.id)
    assert row["rights_from_parent_capture"]
    assert (row["source_url"], row["source_host"]) == (EXTRACT, "download.geofabrik.de")
    assert (row["licence"], row["publication"], row["reviewed_host"]) == (
        "ODbL-1.0",
        "open",
        "geofabrik.de",
    )
    [own] = rights("evidence.capture", capture_id=extract.id)
    assert not own["rights_from_parent_capture"] and own["licence"] == "ODbL-1.0"
    # Without a listed source, a computation stays unqualified rather than guessed.
    [internal] = rights("evidence.capture", capture_id=inventory_capture.id)
    assert (internal["licence"], internal["rights_from_parent_capture"]) == ("unknown", False)


def test_rows_known_by_a_link_take_the_rights_of_its_host(enforce_rights):
    developer = Developer.objects.create(key="aldar", name="Aldar", website_url=ALDAR_PAGE)
    mirrored(enforce_rights)
    [row] = rights("real_estate.developer", row_id=str(developer.id))
    assert row["capture_id"] is None and row["source_url"] == ALDAR_PAGE
    assert (row["reviewed_host"], row["publication"]) == ("aldar.com", "link")
    # A link is not a collection: nothing was read against the terms.
    assert not row["collected_against_terms"]


def test_the_enforcement_switches_are_mirrored_with_their_history(enforce_rights):
    snapshot(project("renad-tower"), PSI_PAGE)
    mirrored(enforce_rights)
    assert rights("evidence.project_snapshot")[0]["shown_beyond_terms"]
    assert apply_source_rights(actor=ACTOR)["enforcement"] == {
        "created": 0,
        "kept": 2,
        "revoked": 0,
    }
    mirrored(enforce_rights, publication=True)
    [row] = rights("evidence.project_snapshot")
    # Withheld once publication is enforced: no longer shown beyond the terms.
    assert row["publication"] == "none" and not row["shown_beyond_terms"]
    history = list(SourceRightsEnforcement.objects.filter(name="publication").order_by("id"))
    assert [(item.enforced, item.active) for item in history] == [(False, False), (True, True)]
    assert history[0].revoked_by == ACTOR


def test_a_revised_review_applies_to_every_row_without_rewriting_it(enforce_rights, monkeypatch):
    snapshot(project("renad-tower"), PSI_PAGE)
    mirrored(enforce_rights)
    rows = list(ProjectSnapshot.objects.values_list("id", "capture_id"))
    revised = tuple(
        {**row, "publication": "facts"} if row["host"] == "psinv.net" else row
        for row in source_rights.source_rights()
    )
    monkeypatch.setattr(source_rights, "source_rights", lambda: revised)
    apply_source_rights(actor=ACTOR)
    [row] = rights("evidence.project_snapshot")
    assert (row["publication"], row["shown_beyond_terms"]) == ("facts", False)
    assert list(ProjectSnapshot.objects.values_list("id", "capture_id")) == rows


def test_the_summary_counts_rows_by_status(enforce_rights):
    renad = project("renad-tower")
    snapshot(renad, PSI_PAGE)
    snapshot(renad, PSI_PAGE.replace("renad-tower-1", "renad-tower-2"))
    mirrored(enforce_rights)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT licence, publication, collected_against_terms, rows, hosts "
            "FROM evidence.data_rights_summary WHERE dataset = 'evidence.project_snapshot'"
        )
        assert cursor.fetchall() == [("proprietary", "none", True, 2, 1)]


def test_every_owned_table_has_a_path_to_its_rights_or_a_reason():
    report = inventory()
    assert report["rights_uncovered"] == []
    tables = {f"{row['schema']}.{row['table']}": row["rights"] for row in report["tables"]}
    # No stale exemption, and no table both exempted and in the view.
    assert set(RIGHTS_EXEMPT) <= set(tables)
    assert {name for name, path in tables.items() if path == "evidence.data_rights"}.isdisjoint(
        RIGHTS_EXEMPT
    )
    assert tables["real_estate.parcel"] == "evidence.data_rights"
    assert tables["evidence.walking_area"] == "evidence.data_rights"
