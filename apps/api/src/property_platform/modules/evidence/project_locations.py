"""Materialize source-declared project positions, separately from parcel ownership."""

import hashlib
import json

from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone

from property_platform.modules.catalog.models import Place
from property_platform.modules.catalog.services import reconcile_map_record, retire_map_record
from property_platform.modules.catalog.territories import TERRITORY_BY_ID

from .models import Capture, IngestionRun, MapObservation, ProjectIdentityLink
from .research_sources import project_marker

VERSION = "project-map-v2"


def extract_project_position(definition, source, receipt):
    if source["role"] != "project" or definition["identity_links"]:
        return None
    marker = project_marker(receipt["payload"], source["url"], definition["name"])
    if marker is None:
        return None
    area = TERRITORY_BY_ID[definition["territory_id"]]
    west, south, east, north = area.bounds
    if not (west <= marker["lon"] <= east and south <= marker["lat"] <= north):
        return None
    return marker


@transaction.atomic
def materialize_project_position(project, capture, marker, *, actor):
    if marker is None:
        return False
    namespace = capture.run.source.key
    previous = ProjectIdentityLink.objects.filter(
        project=project,
        place__source_namespace=namespace,
        place__source_record_id="publisher-map",
    )
    # A rejected identity is not recreated, even if the publisher still repeats it.
    if previous.filter(active=False).exists():
        return False
    if MapObservation.objects.filter(capture=capture, source_record_id="publisher-map").exists():
        return True
    geometry = Point(marker["lon"], marker["lat"], srid=4326)
    place, action, before, after = reconcile_map_record(
        model=Place,
        namespace=namespace,
        record_id="publisher-map",
        values={"name": project.name, "name_ar": "", "kind": "publisher_project_marker"},
        geometry=geometry,
    )
    attributes = {**marker, "location_status": "declared_unverified"}
    MapObservation.objects.create(
        place=place,
        capture=capture,
        source_record_id="publisher-map",
        source_url=capture.url,
        raw_attributes=attributes,
        record_sha256=hashlib.sha256(
            json.dumps(
                {**attributes, "geometry": json.loads(geometry.geojson)},
                sort_keys=True,
            ).encode()
        ).hexdigest(),
        mapping_version=VERSION,
        action=action,
        target_revision=place.revision,
        before=before,
        after=after,
    )
    if not previous.exists():
        ProjectIdentityLink.objects.create(
            project=project,
            place=place,
            capture=capture,
            actor=actor,
            reason=f"Source-declared project position ({marker['method']}); "
            "not a parcel ownership or surveyed boundary assertion.",
        )
    return True


@transaction.atomic
def withdraw_camera_positions(*, actor):
    """Withdraw the early viewport extraction without deleting its evidence."""
    from .project_import import revoke_project_link

    if not isinstance(actor, str) or not actor.strip():
        raise ValueError("A review actor is required")
    ids = (
        MapObservation.objects.filter(
            raw_attributes__method="publisher_map_viewpoint", place__active=True
        )
        .values_list("place_id", flat=True)
        .distinct()
    )
    withdrawn = []
    for place in Place.objects.select_for_update().filter(id__in=ids).order_by("id"):
        observation = (
            MapObservation.objects.filter(place=place, capture__run__status="succeeded")
            .select_related("capture__run__source")
            .order_by("-capture__fetched_at", "-id")
            .first()
        )
        if (
            observation is None
            or observation.raw_attributes.get("method") != "publisher_map_viewpoint"
        ):
            continue
        parent = observation.capture
        run = IngestionRun.objects.create(
            source=parent.run.source,
            actor=actor.strip(),
            connector_version=VERSION,
        )
        capture = Capture.objects.create(
            run=run,
            parent_capture=parent,
            url=parent.url,
            payload=parent.payload,
            byte_length=parent.byte_length,
            content_sha256=parent.content_sha256,
            http_status=parent.http_status,
            fetched_started_at=parent.fetched_started_at,
            fetched_at=parent.fetched_at,
            acquisition_method="source_position_review",
            timestamp_basis="parent_capture_clock",
        )
        reason = "Publisher embed camera centre is not the project pin; position withdrawn."
        for link in ProjectIdentityLink.objects.filter(place=place, active=True):
            revoke_project_link(link.id, actor=actor.strip(), reason=reason)
        retired = retire_map_record(
            model=Place, namespace=place.source_namespace, record_id=place.source_record_id
        )
        attrs = {"reason": reason, "parent_observation_id": observation.id}
        MapObservation.objects.create(
            place=retired,
            capture=capture,
            source_record_id="publisher-map",
            source_url=parent.url,
            raw_attributes=attrs,
            record_sha256=hashlib.sha256(json.dumps(attrs, sort_keys=True).encode()).hexdigest(),
            mapping_version=VERSION,
            action="retired",
            target_revision=retired.revision,
            before={"active": True},
            after={"active": False},
        )
        run.status, run.finished_at = "succeeded", timezone.now()
        run.summary = {"retired_place_id": str(place.id), "reason": reason}
        run.save(update_fields=["status", "finished_at", "summary"])
        withdrawn.append(str(place.id))
    return withdrawn
