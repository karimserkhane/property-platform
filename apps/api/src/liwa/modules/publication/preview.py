"""Local research projection, deliberately distinct from an approved public dossier."""

from liwa.modules.catalog.queries import parcel_features, parcel_identity
from liwa.modules.evidence.onwani import SOURCE_KEY
from liwa.modules.evidence.queries import parcel_provenance


def features(*, bbox, limit, query):
    return parcel_features(namespace=SOURCE_KEY, bbox=bbox, limit=limit, query=query)


def detail(parcel_id):
    parcel = parcel_identity(namespace=SOURCE_KEY, parcel_id=parcel_id)
    if parcel is None:
        return None
    provenance = parcel_provenance(parcel_id=parcel_id, source_key=SOURCE_KEY)
    if provenance is None:
        return None
    return {**parcel, "source": provenance, "publication_status": "local_preview"}
