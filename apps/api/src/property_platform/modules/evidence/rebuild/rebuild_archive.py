"""Private capture replay specification, owned by evidence, never an HTTP data import.

This is not a row/SQL restore: current typed importers parse the original source
bytes again. Every table is compared, including unsupported families; an incomplete
replay is a failed check. Operational audit counts are reported, not equated to the
new execution's audit trail. Operator decisions still require the A03 backup.
"""

import base64
import hashlib
import json
import logging
from collections import deque
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from ..collection_profiles import COLLECTIONS
from ..history.journals import audit_context
from ..history.pipeline_inventory import inventory
from ..media_storage import read_capture
from ..models import BasemapTile, Capture, ImageryScene, IngestionRun, PropertyPresentation
from ..projects import activity_import, project_discovery, project_protocol
from ..sources import abu_dhabi
from . import orchestration, replay_protocols
from . import rebuild_published as published_level

logger = logging.getLogger(__name__)
VERSION = 1
MAX_CAPTURE = 128 * 1024 * 1024
TECHNICAL = {
    "source",
    "capture",
    "ingestion_run",
    "ingestion_execution",
    "ingestion_execution_run",
    "row_revision",
    "audit_event",
    "quarantined_observation",
}
BACKUP_ONLY = {
    "history_exclusion": "Operator withdrawal decisions and revocations",
    "parcel_source_alias": "Reviewed parcel identity decisions",
    "administrative_area_source_alias": "Reviewed area identity decisions",
    "stored_object": "Private object locations and verification receipts",
    "capture_object": "Private object bindings",
    "media_publication": "Operator publication and rights decisions",
    "project_media_publication": "Operator publication and rights decisions",
    "routing_graph": "Routing engine state; restore A03 or rebuild with the routing worker",
    "routing_graph_part": "Routing input fragments; restore A03 or rebuild with the routing worker",
    "walking_request": "User-generated calculation queue",
    "walking_area": "Derived walking calculations require the routing worker",
    "basemap_request": "Demand queue includes requests without any acquired capture",
}
# Derived from the published dossiers, which are compared on their own; reported only.
DERIVED = {
    "evidence_search_entry": "Search index of the published dossiers (E01), rebuilt last",
    "evidence_search_embedding": (
        "Vectors of the search index (E01); only with the optional embeddings service"
    ),
}

# Mirrors of reviewed repository registries, rebuilt from the current file: a difference
# says the reference database has not applied the latest review yet, not that data is lost.
REGISTRY_MIRRORS = {
    "source_rights": "Reviewed source rights, mirrored from source_rights.json",
    "source_rights_enforcement": (
        "Owner's enforcement switches, mirrored from source_rights_enforcement.json"
    ),
}
# A historically unavailable reference is reproduced as unavailable, not as a new failure.
REPLAYED_STATUS = {"failed": "replayed_unavailable"}
# Catalogue identities whose duplicates, created before import-time resolution existed,
# were later superseded by a reviewed repair (kept by A03). The current importer resolves
# the same provider records without creating the duplicate, so these tables compare
# their active identities exactly and require every missing superseded row to be
# accounted for by such a repair.
REVIEWED_SUPERSESSIONS = {
    "real_estate.parcel": ("parcel_source_alias", "superseded_parcel_id"),
    "real_estate.administrative_area": ("administrative_area_source_alias", "superseded_area_id"),
}
# Status divergences reviewed one by one (A14). The original interpretation is not
# reproducible from the repository, and a later run of the SAME bytes recorded the
# outcome the current mapping gives. Each entry is accepted only when the replay matches
# that later run's observations per target; its table effect is then counted apart.
# Any other divergence, a new quarantine included, still fails the check.
REVIEWED_DIVERGENCES = {
    "d7b5f4bc-3390-4e62-85ef-90e765e842c0": {
        "original_status": "quarantined",
        "replayed_status": "succeeded",
        "captures": ("06a6dedd2a03cb679e9dfcdf98145950b66c5b2ca5613d30ae386c56aab64065",),
        "same_as_run": "29a909a9-b094-40e2-aeca-f25b86a950be",
        "reason": "Uncommitted reem-map-v1 interpretation (before 087241d), replaced one "
        "minute later on the same capture; see REBUILD.md",
    },
}
# Map identities an unrecorded interpretation created and a later run of the same
# source withdrew (A15). The current mapping never creates them. Each is accepted only
# when the reference holds it inactive with exactly these two observations (mapping
# version, action) and the replay has no such identity; its rows are then counted apart.
_VIEWPOINT = {
    "observations": (("project-map-v1", "created"), ("project-map-v2", "retired")),
    "reason": "Uncommitted project-map-v1 took the publisher map camera centre for the "
    "project pin; withdrawn by review_project_locations on 16 October (4d2c51f)",
}
WITHDRAWN_ATTRIBUTIONS = {
    **{
        ("place", f"project:{slug}", "publisher-map"): _VIEWPOINT
        for slug in (
            "one-reem-island",
            "reem-eight",
            "reem-eleven",
            "reem-five",
            "reem-nine",
            "saas-heights",
            "seamont",
        )
    },
    ("place", "research:d8fec783bd5e949ef1b5103def6921a5bf1dcd76", "project-map-marker"): {
        "observations": (("reem-references-v1", "created"), ("reem-references-v2", "retired")),
        "reason": "Uncommitted reem-references-v1 marker (before 087241d); reem-references-v2 "
        "retired it on the same bytes as a title mismatch",
    },
}
# Unrecorded interpretations that a later run re-read on the SAME bytes (A15). The
# replayed step must give what that first later run gave; no rule of the unrecorded
# version is guessed.
SUPERSEDED_INTERPRETATIONS = {
    "reem-references-v1": {
        "operation": "references",
        "replaced_by": "reem-references-v2",
        "reason": "Uncommitted (before 087241d); every capture re-read 30 minutes later by "
        "stored_capture_reprocess under reem-references-v2",
    },
}
# Runs whose bytes the current mapping reads more completely, while the reference never
# re-read them (A15). Accepted only for these captures, original rows and replayed rows,
# with the listed identity absent from the reference and active after the replay.
REVIEWED_REINTERPRETATIONS = {
    "a4ad9e09-6c40-4497-9522-f5732d35d8d5": {
        "captures": ("729194b256b9b26f029ece852391212e8cd2edf76ea097f32c8124a638872475",),
        "rows": {"map_observation:place:created": 1},
        "identity": (
            "place",
            "research:601d9da4e13220bd26610a46a33ef374655fc770",
            "project-map-marker",
        ),
        "reason": "bloomholding.com map parser added in 4d2c51f under the unchanged "
        "district-references-v3 version; the 13 October run predates it",
    },
}


def counts():
    """Exact counts, including tables not yet registered with a pipeline."""
    from psycopg import sql

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_type='BASE TABLE' AND table_schema IN ('evidence','real_estate') "
            "ORDER BY 1,2"
        )
        result = {}
        for schema, table in cursor.fetchall():
            cursor.execute(
                sql.SQL("SELECT count(*) FROM {}.{}").format(
                    sql.Identifier(schema), sql.Identifier(table)
                )
            )
            result[f"{schema}.{table}"] = cursor.fetchone()[0]
    return result


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _blob(root, payload):
    digest = hashlib.sha256(payload).hexdigest()
    path = root / "blobs" / digest
    if not path.exists():
        path.write_bytes(payload)
    return digest


def _capture(root, capture):
    payload = read_capture(capture, max_bytes=MAX_CAPTURE)
    if (
        len(payload) != capture.byte_length
        or hashlib.sha256(payload).hexdigest() != capture.content_sha256
    ):
        raise ValueError("Archived capture checksum or size differs")
    return {
        "sha256": _blob(root, payload),
        "byte_length": len(payload),
        "receipt": {
            field: (value.isoformat() if isinstance(value, datetime) else value)
            for field in (
                "url",
                "fetched_started_at",
                "fetched_at",
                "http_status",
                "etag",
                "last_modified_raw",
                "source_published_at",
                "acquisition_method",
                "timestamp_basis",
            )
            for value in (getattr(capture, field),)
        },
    }


def _source_scopes():
    from ..maps import sdi_protocol

    result = {
        sdi_protocol.namespace(scope): ("sdi_parcels", scope)
        for scope in (*COLLECTIONS, *sdi_protocol.district_scopes())
    }
    for area, profile in COLLECTIONS.items():
        result[profile.parcel_namespace] = ("onwani", area)
        for layer in ("district", "community", "street", "osm", "overture"):
            result[profile.map_namespace(layer)] = ("map", f"{area}:{layer}")
        for row in orchestration.reference_registry(area):
            result.setdefault(
                "research:" + orchestration.reference_identity(row["url"]),
                ("references", f"{area}:{orchestration.reference_identity(row['url'])}"),
            )
    for dataset, feed in abu_dhabi.FEEDS.items():
        result[feed.key] = ("public_context", f"abu-dhabi:{dataset}")
    result["adrec:market-data:indices"] = ("adrec_indices", "abu-dhabi")
    for row in project_discovery.catalogue_registry():
        scope = f"{row['territory_scope']}:{row['key']}"
        result[f"project-discovery:{scope}"] = ("project_discovery", scope)
    return result


MAP_TARGETS = ("street", "building", "place", "administrative_area")


def _map_target():
    from django.db.models import Case, CharField, Value, When

    return Case(
        *(When(**{f"{name}__isnull": False}, then=Value(name)) for name in MAP_TARGETS),
        output_field=CharField(),
    )


def run_rows(run_ids=(), *, captures=None, identities=None):
    """Observations written by the given runs, by target and action, plus quarantines.

    `captures` restricts the count to those captures: a project run is replayed one
    registered page at a time. `identities` (target, namespace, record id) keeps only
    the map observations of those identities.

    Diagnostic only: it locates which acquisition explains a table difference (for
    example a historical quarantine accepted at replay); the table policies decide `ok`.
    """
    from django.db.models import Count

    from ..models import MapObservation, ParcelObservation, QuarantinedObservation

    result = {}
    written = Q(capture__run_id__in=run_ids) if captures is None else Q(capture_id__in=captures)
    if identities is not None:
        written &= _identity_filter(identities)
    for row in (
        MapObservation.objects.filter(written)
        .annotate(target=_map_target())
        .values("target", "action")
        .annotate(total=Count("pk"))
        .order_by()
    ):
        result[f"map_observation:{row['target']}:{row['action']}"] = row["total"]
    if identities is not None:
        return result
    for name, model in (
        ("parcel_observation", ParcelObservation),
        ("quarantined_observation", QuarantinedObservation),
    ):
        total = model.objects.filter(written).count()
        if total:
            result[name] = total
    return result


def _identity_filter(identities):
    match = Q(pk__in=[])
    for target, namespace, record_id in identities:
        match |= Q(
            **{f"{target}__source_namespace": namespace, f"{target}__source_record_id": record_id}
        )
    return match


def _reviewed_identity_keys():
    return [
        *WITHDRAWN_ATTRIBUTIONS,
        *(review["identity"] for review in REVIEWED_REINTERPRETATIONS.values()),
    ]


def reviewed_identities():
    """State of the identities the A15 registries name: activity and observations."""
    from ..models import MapObservation

    result = {}
    for target, namespace, record_id in _reviewed_identity_keys():
        model = MapObservation._meta.get_field(target).related_model
        identity = model.objects.filter(
            source_namespace=namespace, source_record_id=record_id
        ).first()
        result["|".join((target, namespace, record_id))] = (
            None
            if identity is None
            else {
                "active": identity.active,
                "observations": sorted(
                    list(row)
                    for row in MapObservation.objects.filter(**{target: identity}).values_list(
                        "mapping_version", "action"
                    )
                ),
            }
        )
    return result


def presentation_bindings():
    """The provider identity and page of every property presentation (A15)."""
    rows = []
    for presentation in PropertyPresentation.objects.select_related("building", "place"):
        target = "building" if presentation.building_id else "place"
        identity = getattr(presentation, target)
        rows.append(
            [target, identity.source_namespace, identity.source_record_id, presentation.website_url]
        )
    return sorted(rows)


def binding_differences(expected, actual):
    """Presentations bound to another identity, missing or added by the replay."""
    from collections import Counter

    before, after = Counter(map(tuple, expected)), Counter(map(tuple, actual))
    return {
        "missing": sorted(list(row) for row in (before - after).elements()),
        "extra": sorted(list(row) for row in (after - before).elements()),
    }


def withdrawn_attributions(expected, actual):
    """Each registered withdrawal, with whether it holds exactly in both databases."""
    result = []
    for key, review in WITHDRAWN_ATTRIBUTIONS.items():
        before, after = expected.get("|".join(key)), actual.get("|".join(key))
        result.append(
            {
                "target": key[0],
                "namespace": key[1],
                "record_id": key[2],
                "observations": len(review["observations"]),
                "matches": before is not None
                and not before["active"]
                and before["observations"] == sorted(list(row) for row in review["observations"])
                and after is None,
                "reason": review["reason"],
            }
        )
    return result


def _without(rows, removed):
    """`rows` minus `removed`, both counts by key."""
    result = {key: total - removed.get(key, 0) for key, total in rows.items()}
    return {key: total for key, total in result.items() if total}


def superseded_reference(step, steps, index):
    """The first later step that re-read the same bytes under the replacing version."""
    review = SUPERSEDED_INTERPRETATIONS.get(step.get("original_version", ""))
    if review is None or step["operation"] != review["operation"]:
        return None
    captures = sorted(c["sha256"] for c in step["captures"])
    return next(
        (
            later
            for later in steps[index + 1 :]
            if later["operation"] == step["operation"]
            and later["scope"] == step["scope"]
            and later.get("original_version") == review["replaced_by"]
            and "original_rows" in later
            and sorted(c["sha256"] for c in later["captures"]) == captures
        ),
        None,
    )


def explain_rows(step, rows, expected, compared, reused, steps, index, reference=None):
    """The rule that accounts for a step's row difference, as (name, detail), or None.

    `expected` is the original rows without registered withdrawn attributions. Each
    rule states an exact condition; its table effect counts apart only when `matches`.
    A difference no rule names stays in the table comparison and fails it.
    """
    if compared is not None:
        # Recorded mapping change: only the observations the legacy rule excludes are
        # set apart, and the rest must equal the original run.
        return "legacy_selection", {
            "version": step["original_version"],
            "excluded": {
                key: total - compared.get(key, 0)
                for key, total in rows.items()
                if total != compared.get(key, 0)
            },
            "matches": _target_totals(compared) == _target_totals(expected),
        }
    if reused:
        # Owner decision (A12): a re-read of an identical receipt is not recreated. It
        # can only have confirmed what the earlier read of the same receipt wrote.
        return "reused_receipt", {
            "not_recreated": expected,
            "matches": all(key.endswith(":unchanged") for key in expected),
        }
    later = superseded_reference(step, steps, index)
    if later is not None:
        same = _without(later["original_rows"], later.get("withdrawn_rows", {}))
        return "superseded_interpretation", {
            "version": step["original_version"],
            "same_as_run": later["run"],
            "reason": SUPERSEDED_INTERPRETATIONS[step["original_version"]]["reason"],
            "matches": _target_totals(rows) == _target_totals(same),
        }
    review = REVIEWED_REINTERPRETATIONS.get(step["run"])
    if review is not None:
        key = "|".join(review["identity"])
        return "reviewed_reinterpretation", {
            "reason": review["reason"],
            "matches": reference is not None
            and key in reference
            and reference[key] is None
            and (reviewed_identities().get(key) or {}).get("active", False)
            and tuple(sorted(c["sha256"] for c in step["captures"])) == review["captures"]
            and not expected
            and rows == review["rows"],
        }
    return None


def legacy_rows(rows, run_ids, selected):
    """`rows` without the replayed observations a legacy OSM mapping could not produce.

    Diagnostic for a recorded mapping change: the replay keeps the current mapping, and
    only the observations it adds under the legacy selection rule are set apart.
    """
    from ..models import MapObservation, QuarantinedObservation

    result = dict(rows)

    def drop(key):
        result[key] -= 1
        if not result[key]:
            del result[key]

    for row in (
        MapObservation.objects.filter(capture__run_id__in=run_ids)
        .annotate(target=_map_target())
        .values("target", "action", "raw_attributes")
    ):
        if not selected(row["target"], (row["raw_attributes"] or {}).get("tags") or {}):
            drop(f"map_observation:{row['target']}:{row['action']}")
    for attributes in QuarantinedObservation.objects.filter(
        capture__run_id__in=run_ids
    ).values_list("raw_attributes", flat=True):
        if not selected(None, (attributes or {}).get("tags") or {}):
            drop("quarantined_observation")
    return result


def _target_totals(rows):
    """Observations per table and map target, whatever the action."""
    totals = {}
    for key, total in rows.items():
        name = key.rsplit(":", 1)[0] if key.startswith("map_observation:") else key
        totals[name] = totals.get(name, 0) + total
    return totals


def reviewed_divergence(step, status, rows, steps_by_run):
    """The registry entry this replayed divergence matches exactly, or None."""
    review = REVIEWED_DIVERGENCES.get(step["run"])
    reference = steps_by_run.get(review["same_as_run"]) if review else None
    if (
        not review
        or reference is None
        or rows is None
        or "original_rows" not in step
        or "original_rows" not in reference
        or step.get("original_status") != review["original_status"]
        or status != review["replayed_status"]
        or tuple(sorted(c["sha256"] for c in step["captures"])) != review["captures"]
        or "quarantined_observation" in rows
    ):
        return None
    if _target_totals(rows) != _target_totals(reference["original_rows"]):
        return None
    return review


def table_deltas(rows, original_rows):
    """Row count differences per owned table written by one step."""
    actual, expected = _target_totals(rows), _target_totals(original_rows)
    deltas = {}
    for name in set(actual) | set(expected):
        table = "evidence." + name.split(":", 1)[0]
        deltas[table] = deltas.get(table, 0) + actual.get(name, 0) - expected.get(name, 0)
    return {table: delta for table, delta in deltas.items() if delta}


def _withdrawn(run_ids=(), *, captures=None):
    """A step's observations of registered withdrawn attributions, when it has any."""
    rows = run_rows(run_ids, captures=captures, identities=list(WITHDRAWN_ATTRIBUTIONS))
    return {"withdrawn_rows": rows} if rows else {}


def ordered_steps(steps):
    """Keep history order inside each phase, with identities before their consumers."""
    phase = {
        "onwani": 0,
        "sdi_parcels": 1,
        "map": 2,
        "osm_bootstrap": 2,
        "references": 3,
        "property_presentations": 4,
        "project_details": 5,
        "project_discovery": 6,
        # Measured parcels are chosen from reviewed project links and positions (B06).
        "construction_activity": 8,
    }
    return sorted(steps, key=lambda step: phase.get(step["operation"], 7))


def export_archive(root: Path, runs=None):
    """One read-only repeatable-read snapshot for captures AND expected counts.

    The private bundle contains source bytes and replay instructions, never arbitrary
    table rows, passwords, user credentials or a SQL dump. `runs` limits the steps to
    these acquisitions (demonstration package, A13); raster scenes and tiles are then
    left out.
    """
    (root / "blobs").mkdir(parents=True, exist_ok=True)
    scopes = _source_scopes()
    projects = {row["slug"]: row for row in project_protocol.project_registry()}
    steps, omitted = [], []
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            cursor.execute("SELECT transaction_timestamp(), pg_current_snapshot()::text")
            instant, snapshot = cursor.fetchone()
        expected, coverage, identity = counts(), inventory(), identities()
        namespace_stats = namespaces()
        reviewed = reviewed_identities()
        bindings = presentation_bindings()
        # What the site publishes, on the same snapshot as the exported captures (A12).
        published = published_level.published_state()
        interpretation = published_level.interpretations()
        selected_runs = IngestionRun.objects.select_related("source").filter(
            Q(status__in=["succeeded", "quarantined"])
            | Q(status="failed", source__key__startswith="research:")
        )
        if runs is not None:
            selected_runs = selected_runs.filter(pk__in=runs)
        for run in selected_runs.order_by("started_at", "pk").iterator(chunk_size=50):
            key = run.source.key
            selection = scopes.get(key)
            operation, scope = selection or (None, None)
            captures = list(Capture.objects.filter(run=run).order_by("ingested_at", "pk"))
            if key.startswith("project:") and key[8:] in projects:
                project = projects[key[8:]]
                used = set()
                for source in project["sources"]:
                    if source["role"] == "terms":
                        continue
                    source_captures = [c for c in captures if c.url == source["url"]]
                    if not source_captures:
                        continue
                    selected = [source_captures[0]]
                    if source.get("terms_url"):
                        selected += [c for c in captures if c.url == source["terms_url"]][:1]
                    used.update(c.pk for c in selected)
                    steps.append(
                        {
                            "operation": "project_details",
                            "scope": f"{project['territory_id']}:{project['slug']}:"
                            + hashlib.sha256(source["url"].encode()).hexdigest(),
                            "run": str(run.pk),
                            # Diagnostic only (A15): this page's observations, not the
                            # whole run; the status is compared through published state.
                            "original_version": run.connector_version,
                            "original_rows": run_rows(captures=[c.pk for c in selected]),
                            **_withdrawn(captures=[c.pk for c in selected]),
                            "captures": [_capture(root, c) for c in selected],
                        }
                    )
                unused = sum(c.pk not in used for c in captures)
                if unused:
                    omitted.append(
                        {
                            "source": key,
                            "run": str(run.pk),
                            "captures": unused,
                            "reason": "Project capture not selected for replay: "
                            "repeated or unregistered URL",
                        }
                    )
                continue
            if key == activity_import.SOURCE_KEY:
                if captures:
                    steps.append(
                        activity_import.export_run(run, lambda capture: _capture(root, capture))
                    )
                continue
            if key.startswith("property:"):
                # These batches span profiles and photo licences. Export their complete
                # per-run receipts and select the reviewed subset during replay.
                operation, scope = "property_presentations", run.source.url
            if key.startswith("adrec:market-data:sales:"):
                from ..models import AdrecMarketSnapshot

                market = AdrecMarketSnapshot.objects.filter(run=run).first()
                if market:
                    operation = "adrec_sales"
                    scope = (
                        f"{market.territory}:adrec-sales:{market.period_start.isoformat()}:"
                        f"{market.period_end.isoformat()}"
                    )
            if operation == "map" and run.connector_version.startswith("osm-api-bootstrap"):
                operation, scope = "osm_bootstrap", scope.split(":")[0]
            if operation and captures:
                targets = []
                if operation == "property_presentations":
                    for presentation in PropertyPresentation.objects.filter(
                        capture__run=run
                    ).select_related("building", "place"):
                        kind = "building" if presentation.building_id else "place"
                        obj = getattr(presentation, kind)
                        targets.append(
                            {
                                "target": kind,
                                "namespace": obj.source_namespace,
                                "record_id": obj.source_record_id,
                            }
                        )
                steps.append(
                    {
                        "operation": operation,
                        "scope": scope,
                        "run": str(run.pk),
                        "original_version": run.connector_version,
                        "original_status": run.status,
                        "original_rows": run_rows([run.pk]),
                        **_withdrawn([run.pk]),
                        "targets": targets,
                        "captures": [_capture(root, c) for c in captures],
                    }
                )
            elif captures and not key.startswith(("basemap:", "sentinel:")):
                omitted.append(
                    {
                        "source": key,
                        "run": str(run.pk),
                        "captures": len(captures),
                        "reason": "No capture replay adapter; see table comparison",
                    }
                )
        # Raster render bytes are source derivatives, not obtainable from STAC JSON alone.
        scenes = []
        for scene in (
            ImageryScene.objects.select_related("capture").order_by("scene_id")
            if runs is None
            else ()
        ):
            scenes.append(
                {
                    "capture": _capture(root, scene.capture),
                    "preview": _blob(root, bytes(scene.preview_png)),
                    "bbox": [scene.west, scene.south, scene.east, scene.north],
                    "render_version": scene.render_version,
                }
            )
        tiles = []
        for tile in (
            BasemapTile.objects.select_related("capture", "request").order_by(
                "capture__fetched_at", "pk"
            )
            if runs is None
            else ()
        ):
            tiles.append(
                {
                    "capture": _capture(root, tile.capture),
                    "provider": tile.request.provider,
                    "z": tile.request.z,
                    "x": tile.request.x,
                    "y": tile.request.y,
                    "provider_version": tile.provider_version,
                    "licence_code": tile.licence_code,
                    "attribution": tile.attribution,
                    "mime_type": tile.mime_type,
                }
            )
        manifest = {
            "version": VERSION,
            "snapshot_at": instant.isoformat(),
            "snapshot": snapshot,
            "expected": expected,
            "identities": identity,
            "namespaces": namespace_stats,
            "reviewed_identities": reviewed,
            "presentation_bindings": bindings,
            "published": published,
            "interpretations": interpretation,
            "coverage": coverage,
            "steps": ordered_steps(steps),
            "scenes": scenes,
            "tiles": tiles,
            "omitted": omitted,
        }
    write_json(root / "manifest.json", manifest)
    return {"steps": len(steps), "tables": len(expected), "snapshot_at": instant.isoformat()}


def load_capture(root, item):
    digest = item["sha256"]
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Invalid archived capture identity")
    path = root / "blobs" / digest
    if path.stat().st_size > MAX_CAPTURE:
        raise ValueError("Capture exceeds replay budget")
    payload = path.read_bytes()
    if len(payload) != item["byte_length"] or hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError("Archived capture checksum or size differs")
    receipt = dict(item["receipt"])
    for key in ("fetched_started_at", "fetched_at", "source_published_at"):
        if receipt.get(key) is not None:
            receipt[key] = datetime.fromisoformat(receipt[key])
    return payload, receipt


def property_receipt(root, item):
    payload, receipt = load_capture(root, item)
    return {
        "url": receipt["url"],
        "http_status": receipt["http_status"],
        "fetched_started_at": receipt["fetched_started_at"].isoformat(),
        "fetched_at": receipt["fetched_at"].isoformat(),
        "sha256": item["sha256"],
        "payload": base64.b64encode(payload).decode("ascii"),
    }


def request_identity(url, params=None):
    # Keep repeated keys: `a=1&a=2` is not the request `a=2`. A request parameter
    # replaces only the keys of its base URL that it provides.
    params = {key: str(value) for key, value in (params or {}).items()}
    parts = urlsplit(url)
    query = [
        pair for pair in parse_qsl(parts.query, keep_blank_values=True) if pair[0] not in params
    ]
    query += params.items()
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(sorted(query)), ""))


class CaptureReplay:
    """Strict ordered responses, no HTTP fallback on a missing or mismatched capture."""

    def __init__(self, root, captures):
        self.root, self.queue = root, deque(captures)

    def __call__(self, url, params):
        if not self.queue:
            raise ValueError("Importer requested a capture absent from the archive")
        item = self.queue.popleft()
        expected, actual = request_identity(url, params), request_identity(item["receipt"]["url"])
        if expected != actual:
            raise ValueError("Importer request differs from the archived receipt URL")
        return load_capture(self.root, item)

    def onwani(self, params=None):
        from ..maps.onwani import BASE_URL

        return self(
            BASE_URL + ("/query" if params else ""),
            {"f": "json", **params} if params else {"f": "pjson"},
        )

    def reference(self, url):
        return self(url, {})

    def assert_consumed(self):
        if self.queue:
            raise ValueError("Importer did not consume its complete archived acquisition")


def identities():
    """Active provider identities and reviewed supersessions of the identity tables."""
    from psycopg import sql

    result = {}
    with connection.cursor() as cursor:
        for table, (alias, column) in REVIEWED_SUPERSESSIONS.items():
            cursor.execute(
                sql.SQL(
                    "SELECT count(*) FILTER (WHERE superseded_by_id IS NULL), "
                    "count(*) FILTER (WHERE superseded_by_id IS NOT NULL), "
                    "md5(coalesce(string_agg(source_namespace || chr(31) || source_record_id, "
                    "chr(30) ORDER BY source_namespace, source_record_id) "
                    "FILTER (WHERE superseded_by_id IS NULL), '')) FROM {}"
                ).format(sql.Identifier(*table.split(".")))
            )
            active, superseded, fingerprint = cursor.fetchone()
            cursor.execute(
                sql.SQL("SELECT count(*) FROM {} WHERE active AND {} IS NOT NULL").format(
                    sql.Identifier("evidence", alias), sql.Identifier(column)
                )
            )
            result[table] = {
                "active": active,
                "superseded": superseded,
                "reviewed_repairs": cursor.fetchone()[0],
                "active_fingerprint": fingerprint,
            }
    return result


# Map identity namespaces this small carry their records in the manifest, so that a
# count difference can be reconciled record by record (A15). Larger ones keep counts
# and a fingerprint only.
NAMESPACE_RECORDS = 200


def namespaces():
    """Map identities per provider namespace: active and inactive counts, fingerprint.

    Diagnostic only: it locates which namespace explains a map table difference; the
    table policies decide `ok`.
    """
    from psycopg import sql

    result = {}
    with connection.cursor() as cursor:
        for target in MAP_TARGETS:
            table = sql.Identifier("real_estate", target)
            cursor.execute(
                sql.SQL(
                    "SELECT source_namespace, count(*) FILTER (WHERE active), "
                    "count(*) FILTER (WHERE NOT active), "
                    "md5(string_agg(source_record_id || chr(31) || active::text, "
                    "chr(30) ORDER BY source_record_id)) FROM {} GROUP BY 1 ORDER BY 1"
                ).format(table)
            )
            stats = {
                namespace: {"active": active, "inactive": inactive, "fingerprint": fingerprint}
                for namespace, active, inactive, fingerprint in cursor.fetchall()
            }
            small = [
                n for n, s in stats.items() if s["active"] + s["inactive"] <= NAMESPACE_RECORDS
            ]
            if small:
                cursor.execute(
                    sql.SQL(
                        "SELECT source_namespace, source_record_id, active FROM {} "
                        "WHERE source_namespace = ANY(%s) ORDER BY 1, 2"
                    ).format(table),
                    [small],
                )
                for namespace, record_id, active in cursor.fetchall():
                    stats[namespace].setdefault("records", []).append([record_id, active])
            result[f"real_estate.{target}"] = stats
    return result


def namespace_differences(expected, actual):
    """Namespaces whose identities differ, with the records when both sides list them."""
    result = {}
    for table in sorted(set(expected) | set(actual)):
        before, after = expected.get(table, {}), actual.get(table, {})
        for namespace in sorted(set(before) | set(after)):
            old, new = before.get(namespace), after.get(namespace)
            if old and new and old["fingerprint"] == new["fingerprint"]:
                continue
            empty = {"active": 0, "inactive": 0, "records": []}
            old, new = old or empty, new or empty
            entry = {
                "expected": {"active": old["active"], "inactive": old["inactive"]},
                "actual": {"active": new["active"], "inactive": new["inactive"]},
            }
            if "records" in old and "records" in new:
                was, now = dict(old["records"]), dict(new["records"])
                entry["missing"] = sorted(set(was) - set(now))
                entry["extra"] = sorted(set(now) - set(was))
                entry["activity_changed"] = sorted(
                    r for r in set(was) & set(now) if was[r] != now[r]
                )
            result.setdefault(table, {})[namespace] = entry
    return result


def identity_matches(expected, actual):
    """Same active identities; only reviewed duplicate repairs may be absent."""
    return (
        expected["active"] == actual["active"]
        and expected["active_fingerprint"] == actual["active_fingerprint"]
        and expected["superseded"] - actual["superseded"]
        == expected["reviewed_repairs"] - actual["reviewed_repairs"]
    )


def compare_tables(
    expected,
    actual,
    expected_identities=None,
    actual_identities=None,
    reviewed_deltas=None,
    history=None,
):
    result = []
    expected_identities, actual_identities = expected_identities or {}, actual_identities or {}
    reviewed_deltas, history = reviewed_deltas or {}, history or {}
    for table in sorted(set(expected) | set(actual)):
        name = table.split(".")[1]
        evidence_table = table.startswith("evidence.")
        reason = BACKUP_ONLY.get(name) if evidence_table else None
        derived = DERIVED.get(name) if evidence_table else None
        mirror = REGISTRY_MIRRORS.get(name) if evidence_table else None
        policy = (
            "backup"
            if reason
            else "derived"
            if derived
            else "registry"
            if mirror
            else ("new_audit" if evidence_table and name in TECHNICAL else "exact")
        )
        reason = reason or derived or mirror
        row = {
            "table": table,
            "expected": expected.get(table),
            "actual": actual.get(table),
            "policy": policy,
            "reason": reason or "",
            "matches": expected.get(table) == actual.get(table),
        }
        if table in expected_identities and table in actual_identities:
            row["policy"] = "identity"
            row["reason"] = "Active identities exact; reviewed duplicate repairs kept by A03"
            row["identities"] = {
                "expected": expected_identities[table],
                "actual": actual_identities[table],
            }
            row["matches"] = identity_matches(expected_identities[table], actual_identities[table])
        elif policy == "exact" and reviewed_deltas.get(table):
            # Only the measured rows of reviewed divergences are counted apart.
            row["reviewed_delta"] = reviewed_deltas[table]
            row["matches"] = (expected.get(table) or 0) + reviewed_deltas[table] == actual.get(
                table
            )
        elif policy == "exact" and table in history:
            # Owner decision (A12): reading history is an alert, published state decides.
            row["policy"], row["reason"] = "history", history[table]
        result.append(row)
    return result


def replay_scenes(root, scenes, actor):
    from ..sources import imagery_import

    if not scenes:
        return
    rows = []
    for item in scenes:
        capture = item["capture"]
        preview = {
            "sha256": item["preview"],
            "byte_length": (root / "blobs" / item["preview"]).stat().st_size,
            "receipt": capture["receipt"],
        }
        raw, _ = load_capture(root, preview)
        rows.append(
            {
                **property_receipt(root, capture),
                "preview": base64.b64encode(raw).decode(),
                "preview_sha256": item["preview"],
                "bbox": item["bbox"],
                "render_version": item["render_version"],
            }
        )
    imagery_import.import_imagery(rows, actor=actor)


def replay_tiles(root, tiles, actor):
    """Revalidate archived tile bytes. No demand queue or failed HTTP response is invented."""
    from ..maps.basemap_archive import checked_tile, validate_tile
    from ..models import BasemapRequest, Source

    for item in tiles:
        provider = item["provider"]
        checked_tile(provider, item["z"], item["x"], item["y"])
        payload, receipt = load_capture(root, item["capture"])
        validate_tile(provider, payload)
        if receipt["http_status"] != 200:
            raise ValueError("An archived tile must have a successful capture")
        with transaction.atomic():
            source, _ = Source.objects.get_or_create(
                key=f"basemap:{provider}", defaults={"name": provider, "url": receipt["url"]}
            )
            run = IngestionRun.objects.create(
                source=source, actor=actor, connector_version="capture-replay-v1"
            )
            capture = Capture.objects.create(
                run=run,
                payload=payload,
                byte_length=len(payload),
                content_sha256=item["capture"]["sha256"],
                **receipt,
            )
            request, _ = BasemapRequest.objects.get_or_create(
                provider=provider,
                z=item["z"],
                x=item["x"],
                y=item["y"],
                defaults={"available": True},
            )
            BasemapTile.objects.create(
                request=request,
                capture=capture,
                **{
                    key: item[key]
                    for key in ("provider_version", "mime_type", "licence_code", "attribution")
                },
            )
            run.status, run.finished_at = "succeeded", timezone.now()
            run.save(update_fields=["status", "finished_at"])


def reviewed_presentations(scope, targets):
    """A shared page cannot fan out a historical receipt to newly reviewed targets."""
    from ..projects import property_import

    selected, photos = [], {}
    identities = {(item["target"], item["namespace"], item["record_id"]) for item in targets}
    for area in COLLECTIONS:
        reviewed, media = property_import.registry(area)
        selected += [
            p
            for p in reviewed
            if p["source_url"] == scope
            and (p["target"], p["namespace"], p["record_id"]) in identities
        ]
        photos.update(media)
    if not selected:
        raise ValueError("Historical presentation target is absent from the reviewed registry")
    return selected, photos


def replay_archive(
    root: Path,
    actor: str,
    run_id: str,
    report_root: Path | None = None,
    *,
    activity_signal=None,
):
    """Called only against the database just created by the ingestion controller.

    ``activity_signal`` is the ingestion change signal of two Sentinel-2 window
    captures (B06): the API runtime never reads rasters itself.
    """
    from ..projects import property_import
    from ..projects.project_market_labels import apply_project_market_labels
    from ..projects.project_relations import apply_project_relations
    from ..projects.project_verification_links import apply_project_verification_links
    from ..search.index import rebuild_search_index
    from ..source_rights_import import apply_source_rights

    def index_search():
        result = rebuild_search_index(actor=actor, run_key="rebuild")
        if result["status"] != "succeeded":
            raise RuntimeError(result.get("error") or "EvidenceSearchFailed")

    manifest = json.loads((root / "manifest.json").read_text("utf-8"))
    if manifest["version"] != VERSION:
        raise ValueError("Unsupported replay manifest")
    outcomes = []
    steps_by_run = {step["run"]: step for step in manifest["steps"]}
    reviewed_deltas = {}
    for index, step in enumerate(manifest["steps"]):
        operation, scope = step["operation"], step["scope"]
        rows = compared = None
        reused = False
        detail = {}
        try:
            execution_key = hashlib.sha256(f"rebuild:{run_id}:{index}".encode()).hexdigest()
            with audit_context(actor=actor, execution_key=execution_key):
                if operation == "property_presentations":
                    profiles, photos = reviewed_presentations(scope, step["targets"])
                    property_import.import_presentations(
                        [property_receipt(root, c) for c in step["captures"]],
                        actor=actor,
                        profiles=profiles,
                        photos=photos,
                    )
                    status = "succeeded"
                elif operation == "construction_activity":
                    if activity_signal is None:
                        raise ValueError("Activity replay requires the ingestion change signal")
                    differences = activity_import.replay_run(
                        step,
                        load=lambda item: load_capture(root, item),
                        actor=actor,
                        run_key=f"construction_activity:{run_id}",
                        signal=activity_signal,
                    )
                    status = "failed" if differences else "succeeded"
                    if differences:
                        detail["measurements"] = differences
                else:
                    replay = CaptureReplay(root, step["captures"])
                    inert = operation in {"project_details", "project_discovery"}
                    result = orchestration.execute_import(
                        operation=operation,
                        scope=scope,
                        actor=actor,
                        execution_key=execution_key,
                        prefect_flow_run_id=run_id,
                        acquisition=None
                        if inert
                        else (
                            replay.onwani
                            if operation == "onwani"
                            else replay.reference
                            if operation == "references"
                            else replay
                        ),
                        receipt=[property_receipt(root, c) for c in step["captures"]]
                        if inert
                        else None,
                        completion_check=None if inert else replay.assert_consumed,
                        historical=replay_protocols.historical_protocol(
                            operation, scope, step.get("original_version", "")
                        ),
                    )
                    status = result["status"]
                    # A reused execution wrote nothing: its runs belong to the earlier
                    # identical receipt that this replay already imported.
                    reused = bool(result.get("reused"))
                    rows = {} if reused else run_rows(result.get("run_ids", []))
                    selected = replay_protocols.legacy_selection(
                        operation, scope, step.get("original_version", "")
                    )
                    if selected and "original_rows" in step and not reused:
                        compared = legacy_rows(rows, result.get("run_ids", []), selected)
                    if operation == "references" and step.get("original_status") == "failed":
                        from ..models import ResearchReference

                        if (
                            status == "failed"
                            and ResearchReference.objects.filter(
                                capture__run_id__in=result["run_ids"], available=False
                            ).exists()
                        ):
                            replay.assert_consumed()
                            status = "replayed_unavailable"
            outcome = {
                "run": step["run"],
                "operation": operation,
                "scope": scope,
                "status": status,
                **detail,
            }
            original = step.get("original_status")
            if (
                original
                and status != "failed"
                and status != REPLAYED_STATUS.get(original, original)
            ):
                # A reproduction keeps the original outcome; a new quarantine or a newly
                # accepted acquisition is a divergence, even when table counts coincide.
                review = reviewed_divergence(
                    step, status, rows if compared is None else compared, steps_by_run
                )
                if review:
                    outcome["reviewed_divergence"] = {
                        "original_status": original,
                        "same_as_run": review["same_as_run"],
                        "reason": review["reason"],
                    }
                    for table, delta in table_deltas(rows, step["original_rows"]).items():
                        reviewed_deltas[table] = reviewed_deltas.get(table, 0) + delta
                else:
                    outcome["diverged_from"] = original
            if "original_rows" in step and rows is not None and rows != step["original_rows"]:
                outcome["rows"] = {"expected": step["original_rows"], "actual": rows}
                # Observations of registered withdrawn attributions are accounted for by
                # identity (A15), after the replay; each rule below sees the rest.
                expected = _without(step["original_rows"], step.get("withdrawn_rows", {}))
                if step.get("withdrawn_rows"):
                    outcome["rows"]["withdrawn"] = step["withdrawn_rows"]
                explained = explain_rows(
                    step,
                    rows,
                    expected,
                    compared,
                    reused,
                    manifest["steps"],
                    index,
                    manifest.get("reviewed_identities"),
                )
                if explained:
                    name, detail = explained
                    outcome[name] = detail
                    if detail["matches"] and not (
                        {"reviewed_divergence", "diverged_from"} & set(outcome)
                    ):
                        deltas = table_deltas(rows, expected)
                        if name == "reviewed_reinterpretation":
                            # The identity it creates is checked by explain_rows.
                            target = REVIEWED_REINTERPRETATIONS[step["run"]]["identity"][0]
                            deltas[f"real_estate.{target}"] = 1
                        for table, delta in deltas.items():
                            reviewed_deltas[table] = reviewed_deltas.get(table, 0) + delta
            outcomes.append(outcome)
        except Exception as exc:
            logger.exception("Rebuild step %s %s failed", operation, scope)
            outcomes.append(
                {
                    "run": step["run"],
                    "operation": operation,
                    "scope": scope,
                    "status": "failed",
                    "error": type(exc).__name__,
                }
            )
        if (index + 1) % 100 == 0:
            logger.info("Replayed %s/%s source steps", index + 1, len(manifest["steps"]))
    for operation, finish in (
        ("basemap_tiles", lambda: replay_tiles(root, manifest["tiles"], actor)),
        ("imagery", lambda: replay_scenes(root, manifest["scenes"], actor)),
        ("project_relations", lambda: apply_project_relations(actor=actor)),
        ("project_verification_links", lambda: apply_project_verification_links(actor=actor)),
        ("project_market_labels", lambda: apply_project_market_labels(actor=actor)),
        ("source_rights", lambda: apply_source_rights(actor=actor)),
        # Last: the index reads the published dossiers the stages above produce (E01).
        ("evidence_search", index_search),
    ):
        try:
            with audit_context(actor=actor):
                finish()
        except Exception as exc:
            logger.exception("Rebuild finishing stage %s failed", operation)
            outcomes.append(
                {"operation": operation, "status": "failed", "error": type(exc).__name__}
            )
    withdrawn = None
    if "reviewed_identities" in manifest:
        # Registered withdrawn attributions are absent from the replay as a whole
        # identity: its row and all its observations count apart, only if exact.
        withdrawn = withdrawn_attributions(manifest["reviewed_identities"], reviewed_identities())
        for item in withdrawn:
            if item["matches"]:
                for table, delta in (
                    (f"real_estate.{item['target']}", -1),
                    ("evidence.map_observation", -item["observations"]),
                ):
                    reviewed_deltas[table] = reviewed_deltas.get(table, 0) + delta
    actual = counts()
    published = None
    if "published" in manifest:
        try:
            published = published_level.compare_published(
                manifest["published"], published_level.published_state()
            )
        except Exception as exc:
            logger.exception("Rebuild published state comparison failed")
            outcomes.append(
                {"operation": "published_state", "status": "failed", "error": type(exc).__name__}
            )
    # A manifest exported before identity statistics keeps the plain exact comparison,
    # and history tables stay exact unless the published state was compared.
    # A demonstration package (A13) has no expected totals: its tables are reported only.
    tables = compare_tables(
        manifest.get("expected", {}),
        actual,
        manifest.get("identities"),
        identities(),
        reviewed_deltas,
        published_level.HISTORY_TABLES if published else None,
    )
    # Diagnostic (A15): which namespaces explain a map table difference. A manifest
    # exported before these statistics has no such detail.
    namespace_diff = (
        namespace_differences(manifest["namespaces"], namespaces())
        if "namespaces" in manifest
        else {}
    )
    for row in tables:
        if namespace_diff.get(row["table"]):
            row["namespaces"] = namespace_diff[row["table"]]
    # Presentations must describe the same provider identities as in the reference;
    # a manifest exported before A15 has no bindings to compare.
    bindings = (
        binding_differences(manifest["presentation_bindings"], presentation_bindings())
        if "presentation_bindings" in manifest
        else None
    )
    coverage = inventory()
    failures = [r for r in outcomes if r["status"] == "failed"]
    divergences = [r for r in outcomes if "diverged_from" in r]
    row_differences = [r for r in outcomes if "rows" in r]
    mismatches = [
        r["table"] for r in tables if r["policy"] in ("exact", "identity") and not r["matches"]
    ]
    history = [r["table"] for r in tables if r["policy"] == "history" and not r["matches"]]
    report = {
        "version": VERSION,
        "checked_at": timezone.now().isoformat(),
        "source_snapshot_at": manifest["snapshot_at"],
        "tables": tables,
        "steps": outcomes,
        "omitted": manifest["omitted"],
        "coverage": coverage,
        "failed_steps": len(failures),
        "diverged_steps": len(divergences),
        "reviewed_divergences": sum("reviewed_divergence" in r for r in outcomes),
        "legacy_selections": sum(
            r.get("legacy_selection", {}).get("matches", False) for r in outcomes
        ),
        **{
            f"{name}s": sum(r.get(name, {}).get("matches", False) for r in outcomes)
            for name in (
                "reused_receipt",
                "superseded_interpretation",
                "reviewed_reinterpretation",
            )
        },
        "withdrawn_attributions": withdrawn,
        "presentation_bindings": bindings,
        # Diagnostic: steps whose observations differ from their original run.
        "row_differences": len(row_differences),
        "namespace_differences": sum(len(v) for v in namespace_diff.values()),
        "mismatches": mismatches,
        # Owner decision (A12): published state blocks, reading history is an alert.
        "published": published,
        "published_blocking": published["blocking"] if published else None,
        "history_differences": history,
        "interpretations": {
            "expected": manifest.get("interpretations"),
            "actual": published_level.interpretations(),
        }
        if published
        else None,
        "requires_backup": [
            r["table"] for r in tables if r["policy"] == "backup" and r["expected"]
        ],
        "ok": not failures
        and not divergences
        and not mismatches
        and not coverage["uncovered"]
        and not (bindings and (bindings["missing"] or bindings["extra"]))
        and (published is None or published["ok"]),
        "scope": "Source capture replay; backup-only state and new audit counts are separate",
    }
    write_json((report_root or root) / "report.json", report)
    return {
        key: report[key]
        for key in (
            "ok",
            "failed_steps",
            "diverged_steps",
            "reviewed_divergences",
            "legacy_selections",
            "reused_receipts",
            "superseded_interpretations",
            "reviewed_reinterpretations",
            "row_differences",
            "namespace_differences",
            "mismatches",
            "published_blocking",
            "history_differences",
            "source_snapshot_at",
        )
    }
