"""Bounded project read models; raw captures, operator details and storage keys stay private."""

from django.db.models import Prefetch

from property_platform.modules.catalog.models import Project

from .models import ProjectIdentityLink, ProjectMedia, ProjectSnapshot


def _source(snapshot, pointer=""):
    return {
        "url": snapshot.capture.url,
        "name": snapshot.project.developer.name,
        "retrieved_at": snapshot.capture.fetched_at,
        "published_at": snapshot.capture.source_published_at,
        "language": snapshot.language,
        "evidence_pointer": pointer,
        "rights_status": snapshot.source_rights_status,
    }


def project_references(target, ids):
    if target not in {"building", "place", "parcel"}:
        return {}
    links = ProjectIdentityLink.objects.filter(
        active=True, capture__run__status="succeeded", **{f"{target}_id__in": ids}
    ).select_related("project")
    return {
        str(getattr(link, f"{target}_id")): {
            "id": link.project.id,
            "slug": link.project.slug,
            "name": link.project.name,
        }
        for link in links
    }


def project_detail(slug):
    project = Project.objects.select_related("developer").filter(slug=slug).first()
    if project is None:
        return None
    snapshots = list(
        ProjectSnapshot.objects.filter(project=project, capture__run__status="succeeded")
        .select_related("capture", "project__developer")
        .defer("capture__payload")
        .prefetch_related(
            "typologies",
            "amenities",
            Prefetch(
                "media",
                queryset=ProjectMedia.objects.exclude(rights_status="blocked")
                .select_related(
                    "asset_capture__run",
                    "rights_capture__run",
                    "projectmediapublication__stored_object",
                )
                .defer("asset_capture__payload", "rights_capture__payload"),
            ),
        )
        .order_by("capture__url", "-capture__fetched_at", "-id")
        .distinct("capture__url")[:100]
    )
    if not snapshots:
        return None
    # Select before bounding history: many checks of one URL cannot hide the
    # current extraction of another source page.
    values = sorted(snapshots, key=lambda row: (row.capture.fetched_at, row.id), reverse=True)
    handover = next((row for row in values if row.handover_precision), None)
    total = next((row for row in values if row.total_units is not None), None)
    typology_source = next((row for row in values if row.typologies.all()), None)
    amenity_source = next((row for row in values if row.amenities.all()), None)
    media, seen = [], set()
    for snapshot in values:
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
    return {
        "id": project.id,
        "slug": project.slug,
        "name": project.name,
        "territory": project.territory_id,
        "website_url": project.website_url,
        "developer": {
            "id": project.developer.id,
            "key": project.developer.key,
            "name": project.developer.name,
            "website_url": project.developer.website_url,
        },
        "summary": next((row.summary for row in values if row.summary), ""),
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
                "source": _source(typology_source, row.evidence_pointer),
            }
            for row in typology_source.typologies.all()
        ]
        if typology_source
        else [],
        "amenities": [
            {
                "code": row.code,
                "label": row.label,
                "original_text": row.original_text,
                "source": _source(amenity_source, row.evidence_pointer),
            }
            for row in amenity_source.amenities.all()
        ]
        if amenity_source
        else [],
        "media": media[:60],
        "sources": [_source(row) for row in values],
    }
