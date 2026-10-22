"""Typed, provider-scoped identity decisions; never a name/proximity identity merge."""

from property_platform.modules.catalog.models import AdministrativeArea, Parcel

from .models import AdministrativeAreaSourceAlias, MapObservation, ParcelSourceAlias


class IdentityConflict(ValueError):
    """Provider identity was reused or a strong match is ambiguous; preserve all rows."""


def _proof(capture, namespace):
    if capture.http_status != 200 or capture.run.source.key != namespace:
        raise IdentityConflict("Alias capture does not belong to the provider namespace")


def _canonical(obj):
    if obj.superseded_by_id is not None:
        raise IdentityConflict("An alias target cannot be a superseded identity")
    return obj


def parcel_values_match(parcel, record, geometry):
    values = record["values"]
    return (
        bool(values["official_plot_id"] and values["code"])
        and parcel.official_plot_id == values["official_plot_id"]
        and parcel.code == values["code"]
        and parcel.municipality == values["municipality"]
        and parcel.district == values["district"]
        and parcel.geometry.equals(geometry)
    )


def resolve_parcel(*, namespace, record, geometry, capture, actor):
    """Existing OBJECTIDs can evolve; a new one needs unchanged stable identity proof."""
    alias = (
        ParcelSourceAlias.objects.select_related("parcel")
        .filter(source_namespace=namespace, source_record_id=record["record_id"], active=True)
        .first()
    )
    if (
        alias is None
        and ParcelSourceAlias.objects.filter(
            source_namespace=namespace,
            source_record_id=record["record_id"],
            active=False,
        ).exists()
    ):
        raise IdentityConflict("This provider alias was revoked; a new explicit review is required")
    records = Parcel.objects.filter(source_namespace=namespace, superseded_by__isnull=True)
    current = (
        _canonical(alias.parcel)
        if alias
        else Parcel.objects.filter(
            source_namespace=namespace, source_record_id=record["record_id"]
        ).first()
    )
    values = record["values"]
    stable = values["official_plot_id"]
    if current is not None:
        _canonical(current)
        if current.official_plot_id and (
            current.official_plot_id != stable
            or current.code != values["code"]
            or current.municipality != values["municipality"]
            or current.district != values["district"]
        ):
            raise IdentityConflict("OBJECTID now identifies another official plot")
        if (
            stable
            and records.filter(
                official_plot_id=stable,
                code=values["code"],
                municipality=values["municipality"],
                district=values["district"],
            )
            .exclude(pk=current.pk)
            .exists()
        ):
            raise IdentityConflict("Official plot has multiple unresolved catalogue identities")
        if (
            not current.official_plot_id
            and stable
            and not (current.code == values["code"] and current.geometry.equals(geometry))
        ):
            raise IdentityConflict("Previously unqualified OBJECTID changed its identity")
        return current.pk
    if not stable:
        return None
    candidates = list(
        records.filter(
            official_plot_id=stable,
            code=values["code"],
            municipality=values["municipality"],
            district=values["district"],
        )
    )
    if not candidates:
        if (
            Parcel.objects.filter(
                official_plot_id=stable,
                municipality=values["municipality"],
                district=values["district"],
                superseded_by__isnull=True,
            )
            .exclude(source_namespace=namespace)
            .exists()
        ):
            raise IdentityConflict(
                "Official plot already owned by another source; explicit review required"
            )
        return None
    if len(candidates) != 1 or not parcel_values_match(candidates[0], record, geometry):
        raise IdentityConflict("New OBJECTID requires a unique unchanged plot identity")
    canonical = candidates[0]
    _proof(capture, namespace)
    ParcelSourceAlias.objects.create(
        source_namespace=namespace,
        source_record_id=record["record_id"],
        parcel=canonical,
        capture=capture,
        actor=actor,
        canonical_revision=canonical.revision,
        reason=(
            "Same provider PLOTID, cadastral code, municipality, district and geometry "
            "after OBJECTID refresh"
        ),
    )
    return canonical.pk


def non_oid_attributes(attributes):
    return {key: value for key, value in attributes.items() if key != "OBJECTID"}


def area_attributes(area):
    observation = (
        MapObservation.objects.filter(
            administrative_area=area,
            capture__http_status=200,
            capture__run__source__key=area.source_namespace,
        )
        .order_by("-capture__fetched_at", "-ingested_at", "-pk")
        .first()
    )
    return non_oid_attributes(observation.raw_attributes) if observation else None


def resolve_administrative_area(
    *, namespace, record_id, values, geometry, attributes, capture, actor
):
    alias = (
        AdministrativeAreaSourceAlias.objects.select_related("administrative_area")
        .filter(
            source_namespace=namespace,
            source_record_id=record_id,
            active=True,
        )
        .first()
    )
    if (
        alias is None
        and AdministrativeAreaSourceAlias.objects.filter(
            source_namespace=namespace,
            source_record_id=record_id,
            active=False,
        ).exists()
    ):
        raise IdentityConflict("This administrative alias was revoked; explicit review is required")
    current = (
        _canonical(alias.administrative_area)
        if alias
        else AdministrativeArea.objects.filter(
            source_namespace=namespace, source_record_id=record_id
        ).first()
    )
    incoming = non_oid_attributes(attributes)
    if current is not None:
        _canonical(current)
        previous = area_attributes(current)
        if previous is not None and previous != incoming:
            raise IdentityConflict("Administrative OBJECTID attributes changed; review identity")
        return current.pk
    candidates, potential = [], []
    for area in AdministrativeArea.objects.filter(
        source_namespace=namespace,
        kind=values["kind"],
        superseded_by__isnull=True,
    ):
        previous = area_attributes(area)
        shape_matches = area.geometry.equals(geometry)
        names_match = (area.name, area.name_ar) == (values["name"], values["name_ar"])
        metadata_matches = previous is not None and previous == incoming
        if shape_matches or names_match or metadata_matches:
            potential.append(area)
        if metadata_matches and shape_matches:
            candidates.append(area)
    if not potential:
        return None
    if len(candidates) != 1 or len(potential) != 1:
        raise IdentityConflict("New administrative OBJECTID has no unique exact source proof")
    canonical = candidates[0]
    _proof(capture, namespace)
    AdministrativeAreaSourceAlias.objects.create(
        source_namespace=namespace,
        source_record_id=record_id,
        administrative_area=canonical,
        capture=capture,
        actor=actor,
        canonical_revision=canonical.revision,
        reason=(
            "Same provider, administrative kind, full non-OBJECTID attributes and geometry "
            "after OBJECTID refresh"
        ),
    )
    return canonical.pk
