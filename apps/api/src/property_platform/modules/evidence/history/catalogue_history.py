"""Recover blank catalogue display fields from typed, accepted observations."""

from django.db.models import F, Q

from ..models import AuditEvent, MapObservation


def recover_display(target, rows):
    fields = (
        ("code", "community", "district", "land_use", "construction_status")
        if target == "parcel"
        else ("name", "name_ar", "kind", "height_m", "levels")
    )
    for row in rows:
        row.setdefault("field_history", {})
    for field in fields:
        missing = {str(row["id"]): row for row in rows if field in row and row[field] in (None, "")}
        if not missing:
            continue
        if target == "parcel":
            candidates = AuditEvent.objects.filter(
                parcel_id__in=missing,
                run__status__in=["succeeded", "quarantined"],
                observation__source_record_id=F("parcel__source_record_id"),
                run__source__key=F("parcel__source_namespace"),
            )
            identity, capture = "parcel_id", "observation__capture__"
            timestamp = "observation__ingested_at"
        else:
            identity, capture = f"{target}_id", "capture__"
            candidates = MapObservation.objects.filter(
                **{
                    f"{identity}__in": missing,
                    "capture__run__status__in": ["succeeded", "quarantined"],
                    "source_record_id": F(f"{target}__source_record_id"),
                    "capture__run__source__key": F(f"{target}__source_namespace"),
                }
            )
            timestamp = "ingested_at"
        candidates = candidates.filter(**{"after__has_key": field}).exclude(
            Q(**{f"after__{field}": ""}) | Q(**{f"after__{field}": None})
        )
        for observation in (
            candidates.order_by(identity, f"-{capture}fetched_at", "-id")
            .distinct(identity)
            .values(identity, "after", f"{capture}url", f"{capture}fetched_at", timestamp)
        ):
            row = missing[str(observation[identity])]
            row[field] = observation["after"][field]
            row["field_history"][field] = {
                "url": observation[f"{capture}url"],
                "retrieved_at": observation[f"{capture}fetched_at"],
                "ingested_at": observation[timestamp],
            }
