"""All-or-nothing typed project extraction from registered, captured sources."""

import functools
import hashlib
import json
from datetime import date
from pathlib import Path

from django.db import connection, transaction
from django.utils import timezone

from property_platform.modules.catalog.models import Building, Parcel, Place
from property_platform.modules.catalog.project_services import reconcile_project

from .models import (
    Capture,
    IngestionRun,
    ProjectAmenity,
    ProjectIdentityLink,
    ProjectMedia,
    ProjectSnapshot,
    ProjectTypology,
    Source,
)

VERSION = "project-details-v5"
LOCK_KEY = 716548220
TARGETS = {"building": Building, "place": Place, "parcel": Parcel}
# Code that turns a receipt into a reading. A declared extractor version can stay the
# same across a code change; this digest identifies the exact code (A12).
INTERPRETATION_MODULES = (
    "project_import",
    "project_protocol",
    "property_protocol",
    "project_adapters",
    "project_psi",
    "project_adrec",
    "project_propertyfinder",
    "project_maryah",
    "project_locations",
    "research_sources",
)


@functools.cache
def interpretation_sha256():
    digest = hashlib.sha256()
    for name in INTERPRETATION_MODULES:
        source = Path(__file__).with_name(f"{name}.py").read_bytes()
        # Same commit, same digest, whatever the checkout's line endings.
        digest.update(name.encode() + b"\0" + source.replace(b"\r\n", b"\n") + b"\0")
    return digest.hexdigest()


def registry_sha256(definition):
    encoded = json.dumps(definition, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _link_reviewed_targets(project, definition, identities, capture, actor):
    from .project_relations import reviewed_capture, same_receipt

    count = 0
    for link in definition["identity_links"]:
        target = link["target"]
        identity = identities[(project.slug, target, link["namespace"], link["record_id"])]
        if identity is None:
            continue
        evidence = capture
        if link.get("reviewed_on"):
            # A dated review cites its page as it stood that day, whatever the import
            # order: an archive rebuild then cites the same capture (A12).
            evidence = reviewed_capture(link["source_url"], link["reviewed_on"])
            if evidence is None:
                continue
        previous = ProjectIdentityLink.objects.filter(project=project, **{target: identity})
        if previous.exists():
            current = previous.filter(active=True).first()
            if (
                current is not None
                and link.get("reviewed_on")
                and not same_receipt(current.capture_id, evidence)
            ):
                # An archived capture of the review day imported later refines the
                # citation; a revoked link stays revoked. The row journal keeps the old one.
                current.capture = evidence
                current.save(update_fields=["capture"])
            continue
        if ProjectIdentityLink.objects.filter(active=True, **{target: identity}).exists():
            raise ValueError("Map identity already belongs to a reviewed project")
        ProjectIdentityLink.objects.create(
            project=project,
            capture=evidence,
            actor=actor.strip(),
            reason=link["reason"],
            **{target: identity},
        )
        count += 1
    return count


def _receipt_key(project, source, receipt, parsed, receipts):
    value = {
        "project": project["slug"],
        "source": source["url"],
        "sha256": receipt["sha256"],
        "fetched_at": receipt["fetched_at"].isoformat(),
        "fetched_started_at": receipt["fetched_started_at"].isoformat(),
        "extractor": parsed["parser_version"],
        "registry_version": VERSION,
        "registry": project,
        "terms": {
            "sha256": receipts[source["terms_url"]]["sha256"],
            "fetched_at": receipts[source["terms_url"]]["fetched_at"].isoformat(),
        }
        if source.get("terms_url") in receipts
        else None,
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _handover_values(value):
    if value is None:
        return {}
    precision = value["precision"]
    year = value["year"]
    quarter, month, day = (value.get(key) for key in ("quarter", "month", "day"))
    if type(year) is not int or not 1900 <= year <= 2200:
        raise ValueError("Invalid handover year")
    if precision == "year" and any(item is not None for item in (quarter, month, day)):
        raise ValueError("Year precision cannot invent a quarter, month or day")
    if precision == "quarter" and (
        type(quarter) is not int or not 1 <= quarter <= 4 or month is not None or day is not None
    ):
        raise ValueError("Invalid handover quarter precision")
    if precision in {"month", "day"}:
        if quarter is not None or type(month) is not int or not 1 <= month <= 12:
            raise ValueError("Invalid handover month")
        if precision == "month" and day is not None:
            raise ValueError("Month precision cannot invent a day")
        if precision == "day":
            date(year, month, day)
    if precision not in {"year", "quarter", "month", "day"}:
        raise ValueError("Invalid handover precision")
    return {
        "handover_precision": precision,
        "handover_year": year,
        "handover_quarter": quarter,
        "handover_month": month,
        "handover_day": day,
        "handover_original": value["original_text"],
        "handover_pointer": value["evidence_pointer"],
    }


def import_project_details(receipt_rows, *, territory, actor):
    """Pure extraction precedes SQL. No promoter images, PDFs or video bodies are fetched here."""
    from .project_locations import extract_project_position, materialize_project_position
    from .project_protocol import (
        extract_project_source,
        project_registry,
        validate_project_receipts,
    )
    from .project_relations import apply_project_relations

    if not isinstance(actor, str) or not 1 <= len(actor.strip()) <= 160:
        raise ValueError("Valid project import actor required")
    definitions = project_registry(territory)
    receipts = validate_project_receipts(receipt_rows, definitions)
    parsed_sources, identities = [], {}
    for definition in definitions:
        for link in definition["identity_links"]:
            target = link["target"]
            if target not in TARGETS:
                raise ValueError("Unknown project identity target")
            filters = {"source_namespace": link["namespace"], "source_record_id": link["record_id"]}
            filters["superseded_by__isnull" if target == "parcel" else "active"] = True
            identities[(definition["slug"], target, link["namespace"], link["record_id"])] = (
                TARGETS[target].objects.filter(**filters).first()
            )
        for source in definition["sources"]:
            parsed = extract_project_source(definition, source, receipts[source["url"]])
            if parsed is not None:
                handover = _handover_values(parsed.get("handover"))
                parsed["map_position"] = extract_project_position(
                    definition, source, receipts[source["url"]]
                )
                parsed_sources.append((definition, source, parsed, handover))
    if not parsed_sources:
        raise ValueError("No usable registered project sources")
    summary = {
        "projects": 0,
        "snapshots": 0,
        "reused": 0,
        "links": 0,
        "locations": 0,
        "typologies": 0,
        "amenities": 0,
        "media_references": 0,
        "run_ids": [],
    }
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [LOCK_KEY])
        projects = {}
        for definition, source, parsed, handover in parsed_sources:
            project = projects.setdefault(definition["slug"], reconcile_project(definition))
            if excluded := source.get("excluded_media_urls"):
                if not source.get("media_review_reason"):
                    raise ValueError("A reviewed media exclusion requires its reason")
                # Explicit source review withdraws a wrong reference without
                # deleting its capture or relying on source disappearance.
                ProjectMedia.objects.filter(
                    snapshot__project=project,
                    snapshot__capture__url=source["url"],
                    source_url__in=excluded,
                    rights_status="reference_only",
                ).update(rights_status="blocked")
            receipt = receipts[source["url"]]
            receipt_key = _receipt_key(definition, source, receipt, parsed, receipts)
            existing = ProjectSnapshot.objects.filter(receipt_key=receipt_key).first()
            if existing is not None:
                summary["links"] += _link_reviewed_targets(
                    project, definition, identities, existing.capture, actor
                )
                summary["reused"] += 1
                summary["run_ids"].append(str(existing.capture.run_id))
                continue
            provider, _ = Source.objects.get_or_create(
                key=f"project:{project.slug}",
                defaults={"name": definition["developer"]["name"], "url": project.website_url},
            )
            run = IngestionRun.objects.create(
                source=provider, actor=actor.strip(), connector_version=VERSION
            )

            def capture(url, acquisition_run=run):
                value = receipts[url]
                return Capture.objects.create(
                    run=acquisition_run,
                    url=url,
                    payload=value["payload"],
                    byte_length=len(value["payload"]),
                    content_sha256=value["sha256"],
                    http_status=200,
                    fetched_started_at=value["fetched_started_at"],
                    fetched_at=value["fetched_at"],
                    acquisition_method="registered_project_receipt",
                    timestamp_basis="receipt_collector_clock",
                )

            evidence = capture(source["url"])
            terms_url = source.get("terms_url")
            terms = capture(terms_url) if terms_url and terms_url in receipts else None
            snapshot = ProjectSnapshot.objects.create(
                project=project,
                capture=evidence,
                terms_capture=terms,
                receipt_key=receipt_key,
                extractor_version=parsed["parser_version"],
                registry_sha256=registry_sha256(definition),
                extractor_sha256=interpretation_sha256(),
                source_role=source["role"],
                source_kind=source.get("source_kind", "developer"),
                source_name=source.get("source_name", definition["developer"]["name"]),
                source_developer_name=parsed.get("source_developer_name", ""),
                source_developer_role=parsed.get("source_developer_role", ""),
                title=parsed["title"],
                summary=parsed.get("summary", ""),
                language=definition.get("language", "en"),
                source_rights_status=source.get("rights_status", "restricted"),
                acquisition_scope=source.get("acquisition_scope", "local_research"),
                actor=actor.strip(),
                total_units=parsed.get("total_units"),
                total_units_basis=parsed.get("total_units_basis", "announced"),
                total_units_original=parsed.get("total_units_original", ""),
                total_units_pointer=parsed.get("total_units_pointer", ""),
                **handover,
            )
            for row in parsed.get("typologies", []):
                ProjectTypology.objects.create(
                    snapshot=snapshot,
                    **{
                        key: row.get(key)
                        for key in (
                            "property_type",
                            "bedrooms",
                            "original_text",
                            "evidence_pointer",
                        )
                    },
                )
                summary["typologies"] += 1
            for row in parsed.get("amenities", []):
                ProjectAmenity.objects.create(
                    snapshot=snapshot,
                    **{
                        key: row[key]
                        for key in ("code", "label", "original_text", "evidence_pointer")
                    },
                )
                summary["amenities"] += 1
            for row in parsed.get("media", []):
                if row.get("rights_status", "reference_only") != "reference_only":
                    raise ValueError("Source extraction cannot approve media redistribution")
                ProjectMedia.objects.create(
                    snapshot=snapshot,
                    rights_status="reference_only",
                    **{
                        key: row[key]
                        for key in (
                            "kind",
                            "role",
                            "title",
                            "mime_type",
                            "source_url",
                            "original_text",
                            "evidence_pointer",
                        )
                    },
                )
                summary["media_references"] += 1
            summary["links"] += _link_reviewed_targets(
                project, definition, identities, evidence, actor
            )
            summary["locations"] += int(
                materialize_project_position(
                    project, evidence, parsed.get("map_position"), actor=actor.strip()
                )
            )
            run.status, run.finished_at = "succeeded", timezone.now()
            run.summary = {
                "project": project.slug,
                "snapshot_id": snapshot.pk,
                "media_policy": "reference_only",
                "acquisition_scope": "local_research",
            }
            run.save(update_fields=["status", "finished_at", "summary"])
            summary["snapshots"] += 1
            summary["run_ids"].append(str(run.id))
        summary["projects"] = len(projects)
        # Components link to their programme once both identities and the cited
        # source capture exist, so archive rebuilds restore the hierarchy too.
        summary["relations"] = apply_project_relations(territory=territory, actor=actor)
    summary["run_ids"] = sorted(set(summary["run_ids"]))
    return summary


def revoke_project_link(link_id, *, actor, reason):
    if not actor.strip() or not reason.strip():
        raise ValueError("Revocation requires an actor and reason")
    with transaction.atomic():
        link = ProjectIdentityLink.objects.select_for_update().get(pk=link_id)
        if not link.active:
            return link
        link.active, link.revoked_at = False, timezone.now()
        link.revoked_by, link.revocation_reason = actor.strip(), reason.strip()
        link.save(update_fields=["active", "revoked_at", "revoked_by", "revocation_reason"])
        return link
