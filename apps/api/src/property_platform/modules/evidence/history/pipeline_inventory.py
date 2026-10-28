"""Explicit lineage of every owned SQL table to its producing/verification flows."""

import hashlib
import json

from django.apps import apps
from django.db import connection
from django.utils import timezone

from ..models import Capture, IngestionRun, Source
from .journals import audit_context

GROUPS = {
    "property-platform-sdi-parcels": {"Parcel", "ParcelObservation", "AuditEvent"},
    "property-platform-parcels": {"Parcel", "ParcelObservation", "AuditEvent"},
    "property-platform-map": {
        "AdministrativeArea",
        "Building",
        "Place",
        "Street",
        "MapObservation",
    },
    "property-platform-presentations": {"PropertyPresentation", "PropertyMedia"},
    "property-platform-project-details": {
        "Developer",
        "Project",
        "ProjectSnapshot",
        "ProjectTypology",
        "ProjectAmenity",
        "ProjectMedia",
        "ProjectIdentityLink",
        "ProjectRelation",
        "ProjectMarketLabel",
        "ProjectVerification",
        "ProjectVerificationLink",
    },
    "property-platform-project-discovery": {"ProjectSourceCandidate"},
    "property-platform-media-storage": {
        "StoredObject",
        "CaptureObject",
        "MediaPublication",
        "ProjectMediaPublication",
    },
    "property-platform-references": {"ResearchReference"},
    "property-platform-source-rights": {"SourceRights"},
    "property-platform-imagery": {"ImageryScene"},
    "property-platform-construction-activity": {"ConstructionActivityMeasurement"},
    "property-platform-adrec-sales": {"AdrecMarketSnapshot", "AdrecSaleObservation"},
    "property-platform-adrec-indices": {"AdrecMarketSnapshot", "AdrecIndexObservation"},
    "property-platform-public-context": {
        "PublicContextSnapshot",
        "HealthFacilityObservation",
        "DistrictBoundaryObservation",
        "SchoolObservation",
        "BusRouteObservation",
        "CensusMeasureObservation",
    },
    "property-platform-basemap-archive": {"BasemapRequest", "BasemapTile"},
    "property-platform-routing-graph": {"RoutingGraph", "RoutingGraphPart"},
    "property-platform-walking-areas": {"WalkingRequest", "WalkingArea"},
    # Operator decisions are verified, never fabricated by a source refresh.
    "property-platform-data-history": {
        "HistoryExclusion",
        "ParcelSourceAlias",
        "AdministrativeAreaSourceAlias",
    },
}
SHARED = {
    "Source",
    "Capture",
    "IngestionRun",
    "IngestionExecution",
    "IngestionExecution_runs",
    "QuarantinedObservation",
    "RowRevision",
}


def inventory():
    with connection.cursor() as cursor:
        cursor.execute("""SELECT n.nspname, c.relname,
            EXISTS(SELECT 1 FROM pg_trigger t WHERE t.tgrelid=c.oid AND NOT t.tgisinternal
                AND t.tgname=CASE WHEN c.relname='row_revision'
                    THEN 'protect_journal' ELSE 'journal_row' END
                AND t.tgenabled='O')
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname IN ('real_estate','evidence') AND c.relkind='r' ORDER BY 1,2""")
        tables = cursor.fetchall()
    models = {
        model._meta.db_table: model.__name__
        for model in apps.get_models(include_auto_created=True)
        if model._meta.app_label in {"evidence", "catalog"}
    }
    rows = []
    for schema, table, audited in tables:
        model = models.get(table)
        flows = (
            sorted(GROUPS)
            if model in SHARED
            else [flow for flow, members in GROUPS.items() if model in members]
        )
        rows.append(
            {
                "schema": schema,
                "table": table,
                "model": model,
                "audited": audited,
                "flows": flows,
                "covered": bool(flows) and audited,
            }
        )
    return {
        "checked_at": timezone.now().isoformat(),
        "tables": rows,
        "uncovered": [f"{r['schema']}.{r['table']}" for r in rows if not r["covered"]],
        "exceptions": [
            {
                "provider": "esri",
                "reason": "Permanent tile archival rights have not been established; "
                "streaming basemap only.",
            }
        ],
        "scope": "Owned business schemas; framework credentials/sessions and the "
        "separate Prefect database are excluded.",
    }


def check_history(*, actor, run_key):
    source, _ = Source.objects.get_or_create(
        key="data-history-inventory",
        defaults={
            "name": "Database history and pipeline coverage",
            "url": "https://property-platform.invalid/internal/history-inventory",
        },
    )
    previous = IngestionRun.objects.filter(
        source=source, actor=actor, connector_version=run_key, status="succeeded"
    ).first()
    if previous:
        return {"status": "succeeded", "summary": previous.summary}
    with audit_context(actor=actor):
        run = IngestionRun.objects.create(source=source, actor=actor, connector_version=run_key)
        report = inventory()
        payload = json.dumps(report, ensure_ascii=False, sort_keys=True).encode()
        Capture.objects.create(
            run=run,
            url=source.url,
            http_status=200,
            fetched_started_at=run.started_at,
            fetched_at=timezone.now(),
            content_sha256=hashlib.sha256(payload).hexdigest(),
            byte_length=len(payload),
            payload=payload,
            acquisition_method="database_inventory",
            timestamp_basis="database_check_clock",
        )
        run.status = "failed" if report["uncovered"] else "succeeded"
        run.error = "UncoveredBusinessTables" if report["uncovered"] else ""
        run.finished_at = timezone.now()
        run.summary = {
            "tables": len(report["tables"]),
            "uncovered": report["uncovered"],
            "exceptions": report["exceptions"],
        }
        run.save(update_fields=["status", "error", "finished_at", "summary"])
        return {"status": run.status, "summary": run.summary}
