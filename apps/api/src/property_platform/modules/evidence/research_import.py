import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone

from property_platform.modules.catalog.models import AdministrativeArea, Place
from property_platform.modules.catalog.services import reconcile_map_record, retire_map_record

from .collection_profiles import DEFAULT_TERRITORY, collection_for
from .models import Capture, IngestionRun, MapObservation, ResearchReference, Source
from .research_sources import page_metadata, project_marker

VERSION = "district-references-v3"
REGISTRY = Path(__file__).with_name("project_sources.json")
MAX_BYTES = 4 * 1024 * 1024


def finish_reference(capture, row, run, *, territory=DEFAULT_TERRITORY):
    profile = collection_for(territory)
    payload, url = bytes(capture.payload), row["url"]
    title, markers = page_metadata(payload)
    marker = project_marker(payload, url, title) if capture.http_status == 200 else None
    place = None
    with transaction.atomic():
        district = AdministrativeArea.objects.filter(
            active=True,
            kind="district",
            name=profile.district_name,
            superseded_by__isnull=True,
        ).first()
        if marker and district:
            point = Point(marker["lon"], marker["lat"], srid=4326)
            if district.geometry.covers(point):
                place, action, before, after = reconcile_map_record(
                    model=Place,
                    namespace=run.source.key,
                    record_id="project-map-marker",
                    values={
                        "name": marker["name"],
                        "name_ar": "",
                        "kind": "broker_project_marker"
                        if row["kind"] == "broker"
                        else "publisher_project_marker",
                    },
                    geometry=point,
                )
                attrs = {"title": title, **marker, "location_status": "declared_unverified"}
                MapObservation.objects.create(
                    place=place,
                    capture=capture,
                    source_record_id="project-map-marker",
                    source_url=url,
                    raw_attributes=attrs,
                    record_sha256=hashlib.sha256(
                        json.dumps(
                            {**attrs, "geometry": json.loads(point.geojson)}, sort_keys=True
                        ).encode()
                    ).hexdigest(),
                    mapping_version=VERSION,
                    action=action,
                    target_revision=place.revision,
                    before=before,
                    after=after,
                )
        elif (
            capture.http_status == 200
            and markers
            and urlparse(url).hostname == "reportagegroup.com"
            and "/projects/" in url
        ):
            # Positive title/marker disagreement invalidates the old v1 attribution.
            retired = retire_map_record(
                model=Place, namespace=run.source.key, record_id="project-map-marker"
            )
            if retired:
                attrs = {
                    "title": title,
                    "reason": "project_marker_title_mismatch",
                    "markers": markers,
                }
                MapObservation.objects.create(
                    place=retired,
                    capture=capture,
                    source_record_id="project-map-marker",
                    source_url=url,
                    raw_attributes=attrs,
                    record_sha256=hashlib.sha256(
                        json.dumps(attrs, sort_keys=True).encode()
                    ).hexdigest(),
                    mapping_version=VERSION,
                    action="retired",
                    target_revision=retired.revision,
                    before={"active": True},
                    after={"active": False},
                )
        reference = ResearchReference.objects.create(
            capture=capture,
            label=row["label"],
            page_title=title,
            source_kind=row["kind"],
            available=capture.http_status == 200,
            place=place,
            mapping_version=VERSION,
        )
        run.status = "succeeded" if capture.http_status == 200 else "failed"
        run.summary = {
            "reference": reference.id,
            "located": place is not None,
            "http_status": capture.http_status,
            "parent_capture": capture.parent_capture_id,
        }
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "summary", "finished_at"])
    return run


def reprocess_reference(reference, *, actor, territory=DEFAULT_TERRITORY):
    parent = reference.capture
    run = IngestionRun.objects.create(
        source=parent.run.source, actor=actor, connector_version=VERSION
    )
    try:
        capture = Capture.objects.create(
            run=run,
            parent_capture=parent,
            url=parent.url,
            payload=parent.payload,
            byte_length=parent.byte_length,
            http_status=parent.http_status,
            content_sha256=parent.content_sha256,
            fetched_started_at=parent.fetched_started_at,
            fetched_at=parent.fetched_at,
            source_published_at=parent.source_published_at,
            etag=parent.etag,
            last_modified_raw=parent.last_modified_raw,
            acquisition_method="stored_capture_reprocess",
            timestamp_basis=parent.timestamp_basis,
        )
        return finish_reference(
            capture,
            {"url": run.source.url, "label": reference.label, "kind": reference.source_kind},
            run,
            territory=territory,
        )
    except Exception as exc:
        run.status, run.error, run.finished_at = "failed", type(exc).__name__, timezone.now()
        run.save(update_fields=["status", "error", "finished_at"])
        return run


def fetch_reference(url):
    """Default bounded acquisition; workers may inject a separately managed transport."""
    started = datetime.now(UTC)
    request = Request(
        url,
        headers={"User-Agent": "PropertyPlatform/0.1 (manual public reference acquisition)"},
    )
    try:
        response = urlopen(request, timeout=18)
    except HTTPError as exc:
        response = exc
    with response:
        payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError("Reference exceeds capture budget")
        return payload, {
            "url": response.geturl(),
            "http_status": response.status,
            "fetched_started_at": started,
            "fetched_at": datetime.now(UTC),
            "etag": response.headers.get("ETag", "")[:500],
            "last_modified_raw": response.headers.get("Last-Modified", "")[:160],
        }


def import_reference(row, *, actor, acquisition=None, territory=DEFAULT_TERRITORY):
    url = row["url"]
    source, _ = Source.objects.get_or_create(
        key="research:" + hashlib.sha256(url.encode()).hexdigest()[:40],
        defaults={"name": row["label"], "url": url},
    )
    run = IngestionRun.objects.create(source=source, actor=actor, connector_version=VERSION)
    try:
        payload, receipt = (acquisition or fetch_reference)(url)
        if len(payload) > MAX_BYTES:
            raise ValueError("Reference exceeds capture budget")
        capture = Capture.objects.create(
            run=run,
            payload=payload,
            byte_length=len(payload),
            content_sha256=hashlib.sha256(payload).hexdigest(),
            **receipt,
        )
        return finish_reference(capture, row, run, territory=territory)
    except Exception as exc:
        run.status, run.error, run.finished_at = "failed", type(exc).__name__, timezone.now()
        run.save(update_fields=["status", "error", "finished_at"])
        return run
