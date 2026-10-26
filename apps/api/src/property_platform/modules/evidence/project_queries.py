"""Bounded project read models; raw captures, operator details and storage keys stay private."""

import json
from urllib.parse import urlsplit

from django.contrib.gis.geos import Polygon
from django.contrib.postgres.expressions import ArraySubquery
from django.db.models import (
    Case,
    Exists,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Concat

from property_platform.modules.catalog.models import Project
from property_platform.modules.catalog.territories import TERRITORY_BY_ID

from .models import (
    HistoryExclusion,
    ProjectAmenity,
    ProjectIdentityLink,
    ProjectMedia,
    ProjectRelation,
    ProjectSnapshot,
    ProjectTypology,
)


def _accepted_snapshots():
    excluded = HistoryExclusion.objects.filter(
        dataset=Concat(Value("project:"), OuterRef("project__slug")),
        record_key=OuterRef("capture__url"),
        active=True,
    )
    # A later reading of the same acquisition (new extractor or registry version)
    # replaces the earlier one, which stays in history: publication follows the
    # latest interpretation of each receipt, as a rebuild from archived bytes does.
    reread = ProjectSnapshot.objects.filter(
        project_id=OuterRef("project_id"),
        capture__url=OuterRef("capture__url"),
        capture__content_sha256=OuterRef("capture__content_sha256"),
        capture__fetched_at=OuterRef("capture__fetched_at"),
        capture__run__status="succeeded",
        ingested_at__gt=OuterRef("ingested_at"),
    )
    return ProjectSnapshot.objects.filter(capture__run__status="succeeded").filter(
        ~Exists(excluded), ~Exists(reread)
    )


def published_slugs():
    """Projects the directory publishes, in a stable order."""
    snapshots = _accepted_snapshots().filter(project_id=OuterRef("id"))
    return list(
        Project.objects.filter(Exists(snapshots)).order_by("slug").values_list("slug", flat=True)
    )


def _relations(project_ids):
    """Active component links whose two projects are both published."""
    accepted = _accepted_snapshots()
    rows = (
        ProjectRelation.objects.filter(active=True)
        .filter(Q(child_id__in=project_ids) | Q(parent_id__in=project_ids))
        .filter(
            Exists(accepted.filter(project_id=OuterRef("child_id"))),
            Exists(accepted.filter(project_id=OuterRef("parent_id"))),
        )
        .select_related("child", "parent", "capture")
        .defer("capture__payload")
        .order_by("parent__name", "component", "child__name")
    )
    parents, components = {}, {}
    for row in rows:
        parents[row.child_id] = row
        components.setdefault(row.parent_id, []).append(row)
    return parents, components


def _relation(row, project):
    """The other project of a relation, with the reviewed component and its evidence."""
    return {
        "slug": project.slug,
        "name": project.name,
        "component": row.component,
        "basis": row.basis,
        "source_url": row.capture.url,
        "retrieved_at": row.capture.fetched_at,
    }


def _visible_links():
    # Match the dossier's geometry rules before limiting or advertising a pin.
    valid = Q(pk__in=[])
    for area in TERRITORY_BY_ID.values():
        envelope = Polygon.from_bbox(area.bounds)
        envelope.srid = 4326
        targets = Q(pk__in=[])
        for target in ("building", "place", "parcel"):
            targets |= Q(
                **{
                    f"{target}__geometry__coveredby": envelope,
                    f"{target}__geometry__isvalid": True,
                    f"{target}__geometry__isempty": False,
                    **(
                        {f"{target}__superseded_by__isnull": True}
                        if target == "parcel"
                        else {f"{target}__active": True}
                    ),
                }
            )
        valid |= Q(project__territory_id=area.id) & targets
    excluded = HistoryExclusion.objects.filter(
        dataset=Concat(Value("project:"), OuterRef("project__slug")),
        record_key=OuterRef("capture__url"),
        active=True,
    )
    return ProjectIdentityLink.objects.filter(
        valid, active=True, capture__run__status="succeeded"
    ).filter(
        ~Exists(excluded),
        Exists(_accepted_snapshots().filter(project_id=OuterRef("project_id"))),
    )


def project_directory(territory=None, *, query="", offset=0, limit=200):
    search = query
    snapshots = _accepted_snapshots().filter(project_id=OuterRef("id"))
    query = Project.objects.filter(Exists(snapshots))
    if territory is not None:
        query = query.filter(territory_id=territory)
    for term in search.split():
        query = query.filter(Q(name__icontains=term) | Q(developer__name__icontains=term))
    total = query.count()
    records = list(
        query.select_related("developer")
        .annotate(
            checked_at=Subquery(
                snapshots.order_by("-capture__fetched_at", "-pk").values("capture__fetched_at")[:1]
            ),
            mapped=Exists(_visible_links().filter(project_id=OuterRef("id"))),
        )
        .order_by("name", "slug")[offset : offset + limit]
    )
    parents, components = _relations([row.id for row in records])
    return {
        "items": [
            {
                "id": row.id,
                "slug": row.slug,
                "name": row.name,
                "territory": row.territory_id,
                "developer": {
                    "id": row.developer.id,
                    "key": row.developer.key,
                    "name": row.developer.name,
                    "website_url": row.developer.website_url,
                },
                "website_url": row.website_url,
                "updated_at": row.checked_at,
                "has_map_identity": row.mapped,
                "parent": _relation(parents[row.id], parents[row.id].parent)
                if row.id in parents
                else None,
                "component_count": len(components.get(row.id, [])),
            }
            for row in records
        ],
        "has_more": offset + len(records) < total,
        "total": total,
        "offset": offset,
    }


def _source(snapshot, pointer=""):
    return {
        "url": snapshot.capture.url,
        "name": snapshot.source_name or snapshot.project.developer.name,
        "kind": snapshot.source_kind,
        "content_sha256": snapshot.capture.content_sha256,
        "developer_name": snapshot.source_developer_name or None,
        "developer_role": snapshot.source_developer_role or None,
        "retrieved_at": snapshot.capture.fetched_at,
        "published_at": snapshot.capture.source_published_at,
        "language": snapshot.language,
        "evidence_pointer": pointer,
        "rights_status": snapshot.source_rights_status,
        "ingested_at": snapshot.ingested_at,
        "historical": snapshot.capture.fetched_at
        < getattr(snapshot, "latest_source_at", snapshot.capture.fetched_at),
    }


def project_references(target, ids):
    if target not in {"building", "place", "parcel"}:
        return {}
    links = _visible_links().filter(**{f"{target}_id__in": ids}).select_related("project")
    return {
        str(getattr(link, f"{target}_id")): {
            "id": link.project.id,
            "slug": link.project.slug,
            "name": link.project.name,
        }
        for link in links
    }


def _proof_sources(snapshots):
    sources = {}
    for snapshot in snapshots:
        key = (
            snapshot.capture.url,
            snapshot.capture.fetched_at,
            snapshot.capture.content_sha256,
        )
        sources.setdefault(key, _source(snapshot))
    return list(sources.values())


def _project_website(project, snapshots):
    if urlsplit(project.website_url).hostname in {"psinv.net", "adrec.gov.ae"}:
        for snapshot in snapshots:
            if (
                snapshot.source_kind in {"developer", "publisher"}
                and snapshot.source_role == "project"
                and "/api/" not in urlsplit(snapshot.capture.url).path
            ):
                return snapshot.capture.url
    return project.website_url


def project_detail(slug):
    # The sheets read delivery history, activity and sales, which build on this module.
    from .activity_sheet import project_activity
    from .market_sheet import project_market
    from .verification_sheet import project_verification_sheet

    project = Project.objects.select_related("developer").filter(slug=slug).first()
    if project is None:
        return None
    accepted = _accepted_snapshots().filter(project=project)

    # Choose the last known nonempty value per source *before* bounding the
    # response. Thousands of later incomplete checks cannot hide an older fact.
    def last_ids(rows):
        return (
            rows.order_by("capture__url", "-capture__fetched_at", "-id")
            .distinct("capture__url")
            .values("pk")
        )

    newest_asset = (
        ProjectMedia.objects.filter(
            snapshot__in=accepted,
            source_url=OuterRef("source_url"),
        )
        .filter(
            ~Exists(
                HistoryExclusion.objects.filter(
                    dataset=f"project:{project.slug}",
                    active=True,
                    record_key=Concat(OuterRef("snapshot__capture__url"), Value("#media")),
                )
            )
        )
        .order_by("-snapshot__capture__fetched_at", "-snapshot_id", "-pk")
    )
    assets = ProjectMedia.objects.filter(pk=Subquery(newest_asset.values("pk")[:1]))
    typologies = (
        ProjectTypology.objects.filter(snapshot__in=accepted)
        .order_by(
            "snapshot__capture__url",
            "property_type",
            "bedrooms",
            "-snapshot__capture__fetched_at",
            "-pk",
        )
        .distinct("snapshot__capture__url", "property_type", "bedrooms")
    )
    amenities = (
        ProjectAmenity.objects.filter(snapshot__in=accepted)
        .order_by("snapshot__capture__url", "code", "-snapshot__capture__fetched_at", "-pk")
        .distinct("snapshot__capture__url", "code")
    )
    candidates = Q(pk__in=Subquery(last_ids(accepted)))
    for rows in (
        accepted.exclude(summary=""),
        accepted.exclude(handover_precision=""),
        accepted.filter(total_units__isnull=False),
        accepted.filter(Exists(ProjectTypology.objects.filter(snapshot_id=OuterRef("pk")))),
        accepted.filter(Exists(ProjectAmenity.objects.filter(snapshot_id=OuterRef("pk")))),
    ):
        candidates |= Q(pk__in=Subquery(last_ids(rows)))
    candidates |= Q(pk__in=Subquery(assets.values("snapshot_id")))
    candidates |= Q(pk__in=Subquery(typologies.values("snapshot_id")))
    candidates |= Q(pk__in=Subquery(amenities.values("snapshot_id")))
    latest = accepted.filter(capture__url=OuterRef("capture__url")).order_by(
        "-capture__fetched_at", "-pk"
    )
    snapshots = list(
        accepted.filter(candidates)
        .annotate(
            source_priority=Case(
                When(source_kind="authority", then=0),
                When(source_kind="developer", then=1),
                When(source_kind="publisher", then=1),
                When(source_kind="broker", then=2),
                default=3,
                output_field=IntegerField(),
            ),
            latest_source_at=Subquery(latest.values("capture__fetched_at")[:1]),
            excluded_fields=ArraySubquery(
                HistoryExclusion.objects.filter(
                    dataset=f"project:{project.slug}", active=True
                ).values("record_key")
            ),
        )
        .select_related("capture", "project__developer")
        .defer("capture__payload")
        .prefetch_related(
            Prefetch("typologies", queryset=typologies),
            Prefetch("amenities", queryset=amenities),
            Prefetch(
                "media",
                queryset=assets.exclude(rights_status="blocked")
                .select_related(
                    "asset_capture__run",
                    "rights_capture__run",
                    "projectmediapublication__stored_object",
                )
                .defer("asset_capture__payload", "rights_capture__payload"),
            ),
        )
        .order_by("source_priority", "-capture__fetched_at", "-id")[:700]
    )
    if not snapshots:
        return None
    # Authority/developer facts precede agency observations; missing facts can
    # still fall back to another source or a preserved historical observation.
    values = snapshots
    excluded = set(values[0].excluded_fields)

    def allowed(row, field):
        return f"{row.capture.url}#{field}" not in excluded

    summary = next((row for row in values if row.summary and allowed(row, "summary")), None)
    handover = next(
        (row for row in values if row.handover_precision and allowed(row, "handover")), None
    )
    total = next(
        (row for row in values if row.total_units is not None and allowed(row, "total_units")), None
    )

    def children(relation, identity):
        seen = set()
        result = []
        for snapshot in values:
            if not allowed(snapshot, relation):
                continue
            for row in getattr(snapshot, relation).all():
                key = identity(row)
                if key not in seen:
                    seen.add(key)
                    result.append((snapshot, row))
        return result

    known_typologies = children("typologies", lambda row: (row.property_type, row.bedrooms))
    known_amenities = children("amenities", lambda row: row.code)
    media, seen = [], set()
    for snapshot in values:
        if not allowed(snapshot, "media"):
            continue
        for asset in snapshot.media.all():
            if asset.source_url in seen:
                continue
            seen.add(asset.source_url)
            url = None
            if asset.rights_status == "approved":
                from .project_media_storage import delivery_url

                url = delivery_url(asset)
            media.append(
                {
                    "id": asset.id,
                    "kind": asset.kind,
                    "role": asset.role,
                    "title": asset.title,
                    "mime_type": asset.mime_type,
                    "source_url": asset.source_url,
                    "original_text": asset.original_text,
                    "rights_status": asset.rights_status,
                    "delivery_url": url,
                    "author": asset.author or None,
                    "licence_code": asset.licence_code or None,
                    "licence_url": asset.licence_url or None,
                    "taken_on": asset.taken_on,
                    "duration_seconds": asset.duration_seconds,
                    "width": asset.width,
                    "height": asset.height,
                    "source": _source(snapshot, asset.evidence_pointer),
                }
            )
    parents, components = _relations([project.id])
    return {
        "id": project.id,
        "slug": project.slug,
        "name": project.name,
        "territory": project.territory_id,
        "website_url": _project_website(project, values),
        "developer": {
            "id": project.developer.id,
            "key": project.developer.key,
            "name": project.developer.name,
            "website_url": project.developer.website_url,
        },
        "summary": summary.summary if summary else "",
        "summary_source": _source(summary) if summary else None,
        "language": values[0].language,
        "updated_at": max(row.capture.fetched_at for row in values),
        "handover": {
            "precision": handover.handover_precision,
            "year": handover.handover_year,
            "quarter": handover.handover_quarter,
            "month": handover.handover_month,
            "day": handover.handover_day,
            "original_text": handover.handover_original,
            "source": _source(handover, handover.handover_pointer),
        }
        if handover
        else None,
        "programme_total": {
            "value": total.total_units,
            "basis": total.total_units_basis,
            "original_text": total.total_units_original,
            "source": _source(total, total.total_units_pointer),
        }
        if total
        else None,
        "typologies": [
            {
                "property_type": row.property_type,
                "bedrooms": row.bedrooms,
                "original_text": row.original_text,
                "source": _source(snapshot, row.evidence_pointer),
            }
            for snapshot, row in known_typologies
        ],
        "amenities": [
            {
                "code": row.code,
                "label": row.label,
                "original_text": row.original_text,
                "source": _source(snapshot, row.evidence_pointer),
            }
            for snapshot, row in known_amenities
        ],
        "media": media[:60],
        "sources": _proof_sources(values),
        "parent": _relation(parents[project.id], parents[project.id].parent)
        if project.id in parents
        else None,
        "components": [_relation(row, row.child) for row in components.get(project.id, [])],
        "map_locations": project_locations(project, language=values[0].language),
        "declared_progress": _declared_progress(accepted),
        "verification": project_verification_sheet(project, accepted),
        "construction_activity": project_activity(project),
        "observed_sales": project_market(project),
    }


def _declared_progress(accepted):
    """Latest completion the authority register declares for the project itself."""
    # A registration that only identifies a component never describes the project.
    snapshot = (
        accepted.filter(
            verification__fact_scope="project", verification__progress_percent__isnull=False
        )
        .select_related("capture", "project__developer", "verification")
        .defer("capture__payload")
        .order_by("-capture__fetched_at", "-id")
        .first()
    )
    if snapshot is None:
        return None
    facts = snapshot.verification
    return {
        "authority": facts.authority,
        "progress_percent": facts.progress_percent,
        "progress_inspected_on": facts.progress_inspected_on,
        "register_status": facts.register_status,
        "off_plan": facts.off_plan,
        "source": _source(snapshot, facts.evidence_pointer),
    }


# How a project position was obtained, from the most to the least precise. A
# declared point is approximate by nature: it locates a project, not its plot.
POINT_METHODS = {
    "authority_registered_project_coordinates": "authority_point",
    "broker_project_coordinates": "broker_point",
    "publisher_map": "publisher_point",
}
LOCATION_PRECISION = {
    "cadastral_parcel": "boundary",
    "building_footprint": "footprint",
    "authority_point": "point",
    "broker_point": "point",
    "publisher_point": "point",
    "declared_point": "point",
}


def location_method(target, observed_method=None):
    if target == "parcel":
        return "cadastral_parcel"
    if target == "building":
        return "building_footprint"
    return POINT_METHODS.get(observed_method, "declared_point")


def project_locations(project, *, language="en"):
    """Explicit active identities only; never locate by a name or island centre."""
    area = TERRITORY_BY_ID.get(project.territory_id)
    if area is None:
        return []
    west, south, east, north = area.bounds
    links = list(
        _visible_links()
        .filter(project=project)
        .select_related("building", "place", "parcel", "capture")
        .defer("capture__payload")
        .order_by("id")[:50]
    )
    from .queries import map_provenances

    points = map_provenances(
        "place", [link.place_id for link in links if link.place_id], include_method=True
    )
    result = []
    for link in links:
        target = "building" if link.building_id else "place" if link.place_id else "parcel"
        record = getattr(link, target)
        if target == "parcel":
            if record.superseded_by_id is not None:
                continue
        elif not record.active:
            continue
        geometry = record.geometry
        if geometry.empty or not geometry.valid:
            continue
        left, bottom, right, top = geometry.extent
        if not (west <= left <= right <= east and south <= bottom <= top <= north):
            continue
        point_source = points.get(str(record.id), {}) if target == "place" else {}
        method = location_method(target, point_source.get("_method"))
        result.append(
            {
                "id": record.id,
                "target": target,
                "method": method,
                "precision": LOCATION_PRECISION[method],
                "name": project.name,
                "geometry": json.loads(geometry.geojson),
                "source": {
                    "url": point_source.get("url", link.capture.url),
                    "name": point_source.get("name", project.developer.name),
                    "kind": point_source.get("kind", "developer"),
                    "retrieved_at": point_source.get("retrieved_at", link.capture.fetched_at),
                    "published_at": point_source.get(
                        "published_at", link.capture.source_published_at
                    ),
                    "language": language,
                    "evidence_pointer": "active_project_identity_link",
                    "rights_status": "restricted",
                },
            }
        )
    return result


def project_location_gaps(territory=None):
    """Published projects without a documented position, easiest to resolve first.

    1: a parent or component is already located, so one review may place it.
    2: a developer or authority page is published, the usual source of a plot.
    3: only agency or media pages; a position needs new evidence.
    """
    accepted = _accepted_snapshots()
    located = _visible_links().filter(project_id=OuterRef("pk"))
    projects = Project.objects.filter(Exists(accepted.filter(project_id=OuterRef("pk"))))
    if territory:
        projects = projects.filter(territory_id=territory)
    rows = list(
        projects.filter(~Exists(located))
        .annotate(
            official=Exists(
                accepted.filter(
                    project_id=OuterRef("pk"), source_kind__in=["developer", "authority"]
                )
            ),
            related=Exists(
                ProjectRelation.objects.filter(active=True).filter(
                    Q(child_id=OuterRef("pk"), parent__projectidentitylink__in=_visible_links())
                    | Q(parent_id=OuterRef("pk"), child__projectidentitylink__in=_visible_links())
                )
            ),
        )
        .order_by("territory_id", "name")
        .values("slug", "name", "territory_id", "official", "related")
    )
    for row in rows:
        row["priority"] = 1 if row["related"] else 2 if row["official"] else 3
    return sorted(rows, key=lambda row: (row["priority"], row["territory_id"], row["name"]))
