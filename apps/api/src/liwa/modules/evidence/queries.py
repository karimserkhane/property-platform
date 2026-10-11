"""Allowlisted provenance reads. Raw payloads and operator identities stay internal."""

from .models import ParcelObservation


def parcel_provenance(*, parcel_id, source_key):
    observation = (
        ParcelObservation.objects.filter(
            parcel_id=parcel_id,
            capture__run__source__key=source_key,
            capture__run__status__in=["succeeded", "quarantined"],
        )
        .order_by("-capture__fetched_at", "-id")
        .values(
            "capture__run__source__name",
            "capture__run__source__url",
            "capture__fetched_at",
            "source_published_at",
            "ingested_at",
        )
        .first()
    )
    if observation is None:
        return None
    return {
        "name": observation["capture__run__source__name"],
        "url": observation["capture__run__source__url"],
        "retrieved_at": observation["capture__fetched_at"],
        "published_at": observation["source_published_at"],
        "ingested_at": observation["ingested_at"],
    }
