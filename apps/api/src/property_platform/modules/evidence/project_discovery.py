"""Exact publisher catalogue observations. Discovery never grants map identity or media rights."""

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .project_protocol import MAX_CAPTURE_BYTES, _Document, project_registry
from .property_protocol import safe_url, validate_receipts

VERSION = "project-catalogues-v1"


def catalogue_registry(territory=None):
    rows = json.loads(Path(__file__).with_name("project_catalogues.json").read_text("utf-8"))
    if territory is not None and territory not in {row["territory_scope"] for row in rows}:
        raise ValueError("Project catalogue territory is not registered")
    return tuple(row for row in rows if territory is None or row["territory_scope"] == territory)


def catalogue_for(scope):
    for row in catalogue_registry():
        if scope == f"{row['territory_scope']}:{row['key']}":
            return row
    raise ValueError("Project catalogue scope is not registered")


def candidates_for(definition, payload):
    if type(payload) is not bytes or not 0 < len(payload) <= MAX_CAPTURE_BYTES:
        raise ValueError("Project catalogue exceeds its response budget")
    rows = []
    if definition["parser"] == "aldar_catalogue_v1":
        envelope = json.loads(payload)
        data = envelope.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("communities"), list):
            raise ValueError("Aldar catalogue response changed")
        items = data["communities"]
        # Detect truncation rather than silently declaring a partial page exhaustive.
        if (
            type(data.get("total")) is not int
            or data["total"] != len(items)
            or not 1 <= len(items) <= 100
        ):
            raise ValueError("Aldar catalogue pagination is incomplete")
        identifiers = set()
        for index, item in enumerate(items):
            identifier, title = item.get("communityId"), item.get("projectName")
            if (
                not isinstance(identifier, str)
                or not re.fullmatch(r"[A-Za-z0-9]{15,18}", identifier)
                or not isinstance(title, str)
                or not title.strip()
                or len(title) > 150
            ):
                raise ValueError("Aldar catalogue project identity changed")
            if identifier in identifiers:
                raise ValueError("Aldar catalogue repeats a project identity")
            identifiers.add(identifier)
            source_url = (
                f"https://searchservice.properties.aldar.com/api/search/communities/{identifier}"
            )
            if definition.get("website_prefix"):
                source_url = urljoin(
                    "https://www.aldar.com/properties/", item.get("communityUrl", "").lstrip("/")
                )
                if not source_url.startswith(definition["website_prefix"]):
                    raise ValueError("Aldar catalogue website location is ambiguous")
            rows.append(
                {
                    "source_url": source_url,
                    "source_record_id": identifier,
                    "title": title,
                    "original_text": title,
                    "evidence_pointer": f"JSON:data.communities[{index}].communityId/projectName",
                }
            )
    elif definition["parser"] == "html_catalogue_v1":
        document = _Document(payload)
        for index, node in enumerate(document.root.walk()):
            if node.tag != "a":
                continue
            original = node.attrs.get("href", "")
            url = urljoin(definition["url"], original)
            parts = urlsplit(url)
            if not safe_url(url) or parts.query or parts.fragment or len(url) > 4000:
                continue
            if not any(
                url.startswith(prefix)
                and url != prefix
                and "/" not in url[len(prefix) :].strip("/")
                for prefix in definition["prefixes"]
            ):
                continue
            text = node.text().strip()[:255]
            rows.append(
                {
                    "source_url": url,
                    "source_record_id": "",
                    "title": text,
                    "original_text": original[:500],
                    "evidence_pointer": f"a:href[{index}]",
                }
            )
    else:
        raise ValueError("Unknown project catalogue parser")
    result = list({row["source_url"]: row for row in rows}.values())
    if not 1 <= len(result) <= 200:
        raise ValueError("Project catalogue is empty or exceeds its candidate budget")
    return result


def import_catalogue(receipt_rows, *, scope, actor):
    from django.db import transaction
    from django.utils import timezone

    from property_platform.modules.catalog.models import Project

    from .models import Capture, IngestionRun, ProjectSourceCandidate, Source

    if not isinstance(actor, str) or not 1 <= len(actor.strip()) <= 160:
        raise ValueError("Catalogue import actor is required")
    definition = catalogue_for(scope)
    receipts = validate_receipts(receipt_rows, {definition["url"]})
    receipt = receipts[definition["url"]]
    candidates = candidates_for(definition, receipt["payload"])
    # Only exact registered URLs in this territory can be linked automatically.
    known = {
        source["url"]: project["slug"]
        for project in project_registry(definition["territory_scope"])
        for source in project["sources"]
        if source["role"] != "terms"
    }
    known.update(
        {
            project["website_url"]: project["slug"]
            for project in project_registry(definition["territory_scope"])
        }
    )
    known.update(
        {
            url: project["slug"]
            for project in project_registry(definition["territory_scope"])
            for url in project.get("url_aliases", [])
        }
    )
    projects = {
        project.slug: project for project in Project.objects.filter(slug__in=known.values())
    }
    with transaction.atomic():
        provider, _ = Source.objects.get_or_create(
            key=f"project-discovery:{scope}",
            defaults={"name": definition["publisher_key"], "url": definition["url"]},
        )
        run = IngestionRun.objects.create(
            source=provider, actor=actor.strip(), connector_version=VERSION
        )
        capture = Capture.objects.create(
            run=run,
            url=definition["url"],
            payload=receipt["payload"],
            byte_length=len(receipt["payload"]),
            content_sha256=receipt["sha256"],
            fetched_at=receipt["fetched_at"],
            fetched_started_at=receipt["fetched_started_at"],
            http_status=200,
            acquisition_method="registered_project_catalogue",
            timestamp_basis="receipt_collector_clock",
        )
        registered = 0
        for row in candidates:
            project = projects.get(known.get(row["source_url"]))
            registered += project is not None
            ProjectSourceCandidate.objects.create(
                capture=capture,
                project=project,
                publisher_key=definition["publisher_key"],
                territory_scope=definition["territory_scope"],
                status="registered" if project is not None else "pending_review",
                actor=actor.strip(),
                source_url_sha256=hashlib.sha256(row["source_url"].encode()).hexdigest(),
                **row,
            )
        run.summary = {
            "candidates": len(candidates),
            "registered": registered,
            "pending_review": len(candidates) - registered,
            "territory_scope_is_not_a_location_claim": True,
        }
        run.status, run.finished_at = "succeeded", timezone.now()
        run.save(update_fields=["summary", "status", "finished_at"])
    return run
