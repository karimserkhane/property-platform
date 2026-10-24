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

from . import abu_dhabi, orchestration, project_discovery, project_protocol, replay_protocols
from . import rebuild_published as published_level
from .collection_profiles import COLLECTIONS
from .history import audit_context
from .media_storage import read_capture
from .models import BasemapTile, Capture, ImageryScene, IngestionRun, PropertyPresentation
from .pipeline_inventory import inventory

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
    from . import sdi_protocol

    result = {}
    for area, profile in COLLECTIONS.items():
        result[profile.parcel_namespace] = ("onwani", area)
        result[sdi_protocol.namespace(area)] = ("sdi_parcels", area)
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


def run_rows(run_ids):
    """Observations written by the given runs, by target and action, plus quarantines.

    Diagnostic only: it locates which acquisition explains a table difference (for
    example a historical quarantine accepted at replay); the table policies decide `ok`.
    """
    from django.db.models import Count

    from .models import MapObservation, ParcelObservation, QuarantinedObservation

    result = {}
    for row in (
        MapObservation.objects.filter(capture__run_id__in=run_ids)
        .annotate(target=_map_target())
        .values("target", "action")
        .annotate(total=Count("pk"))
        .order_by()
    ):
        result[f"map_observation:{row['target']}:{row['action']}"] = row["total"]
    for name, model in (
        ("parcel_observation", ParcelObservation),
        ("quarantined_observation", QuarantinedObservation),
    ):
        total = model.objects.filter(capture__run_id__in=run_ids).count()
        if total:
            result[name] = total
    return result


def legacy_rows(rows, run_ids, selected):
    """`rows` without the replayed observations a legacy OSM mapping could not produce.

    Diagnostic for a recorded mapping change: the replay keeps the current mapping, and
    only the observations it adds under the legacy selection rule are set apart.
    """
    from .models import MapObservation, QuarantinedObservation

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
    }
    return sorted(steps, key=lambda step: phase.get(step["operation"], 7))


def export_archive(root: Path):
    """One read-only repeatable-read snapshot for captures AND expected counts.

    The private bundle contains source bytes and replay instructions, never arbitrary
    table rows, passwords, user credentials or a SQL dump.
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
        # What the site publishes, on the same snapshot as the exported captures (A12).
        published = published_level.published_state()
        interpretation = published_level.interpretations()
        for run in (
            IngestionRun.objects.select_related("source")
            .filter(
                Q(status__in=["succeeded", "quarantined"])
                | Q(status="failed", source__key__startswith="research:")
            )
            .order_by("started_at", "pk")
            .iterator(chunk_size=50)
        ):
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
            if key.startswith("property:"):
                # These batches span profiles and photo licences. Export their complete
                # per-run receipts and select the reviewed subset during replay.
                operation, scope = "property_presentations", run.source.url
            if key.startswith("adrec:market-data:sales:"):
                from .models import AdrecMarketSnapshot

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
        for scene in ImageryScene.objects.select_related("capture").order_by("scene_id"):
            scenes.append(
                {
                    "capture": _capture(root, scene.capture),
                    "preview": _blob(root, bytes(scene.preview_png)),
                    "bbox": [scene.west, scene.south, scene.east, scene.north],
                    "render_version": scene.render_version,
                }
            )
        tiles = []
        for tile in BasemapTile.objects.select_related("capture", "request").order_by(
            "capture__fetched_at", "pk"
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
        from .onwani import BASE_URL

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
        policy = (
            "backup"
            if reason
            else ("new_audit" if evidence_table and name in TECHNICAL else "exact")
        )
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
    from . import imagery_import

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
    from .basemap_archive import checked_tile, validate_tile
    from .models import BasemapRequest, Source

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
    from . import property_import

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


def replay_archive(root: Path, actor: str, run_id: str):
    """Called only against the database just created by the ingestion controller."""
    from . import property_import
    from .project_relations import apply_project_relations

    manifest = json.loads((root / "manifest.json").read_text("utf-8"))
    if manifest["version"] != VERSION:
        raise ValueError("Unsupported replay manifest")
    outcomes = []
    steps_by_run = {step["run"]: step for step in manifest["steps"]}
    reviewed_deltas = {}
    for index, step in enumerate(manifest["steps"]):
        operation, scope = step["operation"], step["scope"]
        rows = compared = None
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
                    rows = run_rows(result.get("run_ids", []))
                    selected = replay_protocols.legacy_osm_selection(
                        operation, scope, step.get("original_version", "")
                    )
                    if selected and "original_rows" in step:
                        compared = legacy_rows(rows, result.get("run_ids", []), selected)
                    if operation == "references" and step.get("original_status") == "failed":
                        from .models import ResearchReference

                        if (
                            status == "failed"
                            and ResearchReference.objects.filter(
                                capture__run_id__in=result["run_ids"], available=False
                            ).exists()
                        ):
                            replay.assert_consumed()
                            status = "replayed_unavailable"
            outcome = {"run": step["run"], "operation": operation, "scope": scope, "status": status}
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
                if compared is not None:
                    # Recorded mapping change: only the observations the legacy rule
                    # excludes are set apart, and the rest must equal the original run.
                    matches = _target_totals(compared) == _target_totals(step["original_rows"])
                    outcome["legacy_selection"] = {
                        "version": step["original_version"],
                        "excluded": {
                            key: total - compared.get(key, 0)
                            for key, total in rows.items()
                            if total != compared.get(key, 0)
                        },
                        "matches": matches,
                    }
                    if matches and not ({"reviewed_divergence", "diverged_from"} & set(outcome)):
                        for table, delta in table_deltas(rows, step["original_rows"]).items():
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
    ):
        try:
            with audit_context(actor=actor):
                finish()
        except Exception as exc:
            logger.exception("Rebuild finishing stage %s failed", operation)
            outcomes.append(
                {"operation": operation, "status": "failed", "error": type(exc).__name__}
            )
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
    tables = compare_tables(
        manifest["expected"],
        actual,
        manifest.get("identities"),
        identities(),
        reviewed_deltas,
        published_level.HISTORY_TABLES if published else None,
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
        # Diagnostic: steps whose observations differ from their original run.
        "row_differences": len(row_differences),
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
        and (published is None or published["ok"]),
        "scope": "Source capture replay; backup-only state and new audit counts are separate",
    }
    write_json(root / "report.json", report)
    return {
        key: report[key]
        for key in (
            "ok",
            "failed_steps",
            "diverged_steps",
            "reviewed_divergences",
            "legacy_selections",
            "row_differences",
            "mismatches",
            "published_blocking",
            "history_differences",
            "source_snapshot_at",
        )
    }
