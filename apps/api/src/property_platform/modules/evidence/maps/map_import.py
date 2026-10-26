"""Transactional materialisation of independent, source-owned map layers."""

import hashlib
import json
import math
from datetime import datetime

from django.contrib.gis.geos import LineString, MultiLineString, Point
from django.db import connection, transaction
from django.utils import timezone

from property_platform.modules.catalog.models import AdministrativeArea, Building, Place, Street
from property_platform.modules.catalog.services import geometry_from_rings, reconcile_map_record

from ..collection_profiles import DEFAULT_TERRITORY, collection_for
from ..models import Capture, IngestionRun, MapObservation, QuarantinedObservation, Source
from ..runs import mark_failed
from . import map_sources as protocol
from .identity_resolution import resolve_administrative_area
from .onwani import SourceError, object_ids

TARGETS = {
    "street": Street,
    "building": Building,
    "place": Place,
    "administrative_area": AdministrativeArea,
}
LOCK_KEY = 716548220


class RateLimited(SourceError):
    pass


def acquire(run, url, params, replay=None, acquisition=None):
    payload, receipt = (
        replay if replay is not None else (acquisition or protocol.fetch_url)(url, params)
    )
    capture = Capture.objects.create(
        run=run,
        payload=payload,
        byte_length=len(payload),
        content_sha256=hashlib.sha256(payload).hexdigest(),
        **receipt,
    )
    if receipt["http_status"] == 429:
        raise RateLimited("Map provider rate limited this collection")
    if receipt["http_status"] != 200:
        raise SourceError("Map source returned non-success status")
    return protocol.decode(payload), capture


def official_records(run, layer, acquisition=None, territory=DEFAULT_TERRITORY):
    url, where, geometry_type, fields = collection_for(territory).map_layers()[layer]
    meta, _ = acquire(run, url, {"f": "pjson"}, acquisition=acquisition)
    if meta.get("geometryType") != geometry_type or not set(fields.split(",")).issubset(
        {f["name"] for f in meta.get("fields", [])}
    ):
        raise SourceError("Map source schema changed")
    listing, _ = acquire(
        run,
        url + "/query",
        {"f": "json", "where": where, "returnIdsOnly": "true"},
        acquisition=acquisition,
    )
    ids = object_ids(listing)
    seen = set()
    staged = []
    for offset in range(0, len(ids), 100):
        batch_ids = ids[offset : offset + 100]
        batch, capture = acquire(
            run,
            url + "/query",
            {
                "f": "json",
                "where": where,
                "objectIds": ",".join(map(str, batch_ids)),
                "outFields": fields,
                "outSR": 4326,
                "returnGeometry": "true",
            },
            acquisition=acquisition,
        )
        if batch.get("spatialReference", {}).get("wkid") != 4326:
            raise SourceError("Unexpected map CRS")
        for f in batch.get("features", []):
            attrs = f["attributes"]
            oid = attrs.get("OBJECTID")
            if type(oid) is not int or oid not in batch_ids or oid in seen:
                raise SourceError("Unexpected map source identity")
            seen.add(oid)
            shape = f.get("geometry", {})
            if layer == "street":
                paths = [protocol.coordinates(p) for p in shape.get("paths", [])]
                geometry = MultiLineString(*[LineString(p) for p in paths], srid=4326)
                values = {
                    "name": protocol.text(attrs.get("ROADNAME_EN") or attrs.get("NAME_EN")),
                    "name_ar": protocol.text(attrs.get("ROADNAME_AR") or attrs.get("NAME_AR")),
                    "kind": protocol.text(attrs.get("ROADTYPE_EN"), 100),
                }
                target = "street"
            else:
                rings = [protocol.coordinates(p, closed=True) for p in shape.get("rings", [])]
                geometry = geometry_from_rings(rings)
                values = {
                    "name": protocol.text(
                        attrs.get("NAMEENGLISH") or attrs.get("COMMUNITYNAMEENG")
                    ),
                    "name_ar": protocol.text(
                        attrs.get("NAMEARABIC") or attrs.get("COMMUNITYNAMEARA")
                    ),
                    "kind": layer,
                }
                target = "administrative_area"
            if not geometry.valid or geometry.empty:
                raise SourceError("Invalid official map geometry")
            staged.append((target, str(oid), values, geometry, attrs, capture, url, None))
        if set(batch_ids) - seen:
            raise SourceError("Incomplete official map batch")
    latest, _ = acquire(
        run,
        url + "/query",
        {"f": "json", "where": where, "returnIdsOnly": "true"},
        acquisition=acquisition,
    )
    if set(object_ids(latest)) != seen:
        raise SourceError("Map coverage changed during acquisition")
    return staged, []


def number(value, maximum, *, integer=False):
    try:
        n = float(str(value).removesuffix(" m"))
    except TypeError, ValueError:
        return None
    return (
        int(n)
        if integer and n.is_integer() and 0 < n <= maximum
        else (n if not integer and math.isfinite(n) and 0 < n <= maximum else None)
    )


def osm_records(run, replay=None, acquisition=None, territory=DEFAULT_TERRITORY, query=None):
    query = query or collection_for(territory).osm_query
    from urllib.error import URLError

    try:
        data, capture = acquire(
            run,
            protocol.OSM_URL,
            {"data": query},
            replay=replay,
            acquisition=acquisition,
        )
    except RateLimited:
        raise
    except SourceError, URLError, TimeoutError:
        if replay is not None:
            raise
        # One sequential fallback, never an unbounded retry loop or visitor-triggered request.
        data, capture = acquire(
            run,
            protocol.OSM_MIRROR,
            {"data": query},
            acquisition=acquisition,
        )
    return osm_data_records(data, capture, territory=territory)


def osm_data_records(data, capture, *, territory=DEFAULT_TERRITORY, xml_snapshot=False):
    profile = collection_for(territory)
    elements = data.get("elements")
    if (
        not isinstance(elements, list)
        or not 1 <= len(elements) <= 20000
        or (not data.get("osm3s", {}).get("timestamp_osm_base") and not xml_snapshot)
    ):
        raise SourceError("Incomplete OSM snapshot")
    district = AdministrativeArea.objects.get(
        active=True,
        kind="district",
        name=profile.district_name,
        source_namespace=profile.map_namespace("district"),
        superseded_by__isnull=True,
    ).geometry
    staged, rejected, seen = [], [], set()
    for e in elements:
        oid, kind = e.get("id"), e.get("type")
        if type(oid) is not int or oid <= 0 or kind not in ("node", "way", "relation"):
            raise SourceError("Invalid OSM identity")
        identity = f"{kind}/{oid}"
        if identity in seen:
            raise SourceError("Duplicate OSM identity")
        seen.add(identity)
        tags = e.get("tags", {})
        attrs = {
            "id": oid,
            "type": kind,
            "version": e.get("version"),
            "timestamp": e.get("timestamp"),
            "tags": tags,
        }
        name = protocol.text(tags.get("name:en") or tags.get("name"))
        values = {"name": name, "name_ar": protocol.text(tags.get("name:ar")), "kind": ""}
        try:
            published = datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
            if published.tzinfo is None:
                raise ValueError("OSM edit timestamp must be timezone-aware")
            if kind == "node":
                point = Point(e["lon"], e["lat"], srid=4326)
            elif e.get("center"):
                point = Point(e["center"]["lon"], e["center"]["lat"], srid=4326)
            elif kind == "way" and e.get("geometry"):
                coords = [[p["lon"], p["lat"]] for p in e["geometry"]]
                protocol.coordinates(coords, closed=bool(tags.get("building")))
                shape = (
                    geometry_from_rings([coords])
                    if tags.get("building")
                    else MultiLineString(LineString(coords), srid=4326)
                )
                point = shape.centroid
                attrs["location_method"] = "geometry_centroid"
            elif kind == "relation" and e.get("bounds"):
                b = e["bounds"]
                point = Point(
                    (b["minlon"] + b["maxlon"]) / 2, (b["minlat"] + b["maxlat"]) / 2, srid=4326
                )
                attrs["location_method"] = "bounding_box_center"
            else:
                raise ValueError("Missing OSM centre")
            if not district.covers(point):
                continue
            url = "https://www.openstreetmap.org/" + identity
            if kind == "way" and (tags.get("building") or tags.get("highway")):
                coords = [[p["lon"], p["lat"]] for p in e.get("geometry", [])]
                if tags.get("building"):
                    protocol.coordinates(coords, closed=True)
                    shape = geometry_from_rings([coords])
                    attrs_build = {
                        **values,
                        "kind": protocol.text(tags.get("building"), 100),
                        "height_m": number(tags.get("height"), 1000),
                        "levels": number(tags.get("building:levels"), 200, integer=True),
                    }
                    staged.append(
                        ("building", identity, attrs_build, shape, attrs, capture, url, published)
                    )
                elif name:
                    protocol.coordinates(coords)
                    shape = MultiLineString(LineString(coords), srid=4326)
                    staged.append(
                        (
                            "street",
                            identity,
                            {**values, "kind": protocol.text(tags["highway"], 100)},
                            shape,
                            attrs,
                            capture,
                            url,
                            published,
                        )
                    )
            place_kind = protocol.osm_place_kind(tags, named=bool(name or values["name_ar"]))
            if place_kind:
                staged.append(
                    (
                        "place",
                        identity,
                        {**values, "kind": protocol.text(place_kind, 100)},
                        point,
                        attrs,
                        capture,
                        url,
                        published,
                    )
                )
        except ValueError, KeyError, TypeError:
            rejected.append((identity, attrs, capture))
    return staged, rejected


def import_map_layer(
    *, layer, actor, replay=None, acquisition=None, territory=DEFAULT_TERRITORY, historical=None
):
    """`historical` reissues a recorded OSM request during capture replay only."""
    profile = collection_for(territory)
    if historical is not None and (layer != "osm" or not historical.osm_query):
        raise ValueError("A historical protocol applies to its own OSM request only")
    if connection.vendor != "postgresql":
        raise ValueError("Map acquisition requires PostGIS")
    if layer == "overture":
        from .overture_places import import_places

        return import_places(territory=territory, actor=actor, acquisition=acquisition)
    if layer not in (*protocol.LAYERS, "osm"):
        raise ValueError("Unknown map connector")
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [LOCK_KEY])
        if not cursor.fetchone()[0]:
            raise ValueError("Map acquisition already running")
    run = None
    try:
        namespace = profile.map_namespace(layer)
        source, _ = Source.objects.get_or_create(
            key=namespace,
            defaults={
                "name": f"OpenStreetMap — {profile.name} (ODbL)"
                if layer == "osm"
                else f"DMT / Onwani — {profile.name} {layer}",
                "url": protocol.OSM_URL if layer == "osm" else profile.map_layers()[layer][0],
            },
        )
        run = IngestionRun.objects.create(
            source=source,
            actor=actor,
            connector_version=historical.version if historical else protocol.VERSION,
        )
        staged, rejected = (
            osm_records(
                run,
                replay=replay,
                acquisition=acquisition,
                territory=territory,
                query=historical.osm_query if historical else None,
            )
            if layer == "osm"
            else official_records(run, layer, acquisition=acquisition, territory=territory)
        )
        # Observations name the current mapper, the run names the request it reissued.
        return materialize_map_records(
            run, namespace, staged, rejected, actor=actor, mapping_version=protocol.VERSION
        )
    except Exception as exc:
        if run:
            mark_failed(run, exc)
        raise
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [LOCK_KEY])


def materialize_map_records(
    run,
    namespace,
    staged,
    rejected,
    *,
    actor,
    quarantine_reason="Invalid OSM geometry or metadata; not repaired",
    mapping_version=None,
):
    if not staged:
        raise SourceError("No valid map records; previous snapshot preserved")
    summary = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "quarantined": len(rejected),
        "records": len(staged),
    }
    with transaction.atomic():
        for identity, attrs, capture in rejected:
            QuarantinedObservation.objects.create(
                capture=capture,
                source_record_id=identity,
                field_path="elements",
                raw_attributes=attrs,
                reason=quarantine_reason,
            )
        for target, identity, values, shape, attrs, capture, url, published in staged:
            canonical_id = (
                resolve_administrative_area(
                    namespace=namespace,
                    record_id=identity,
                    values=values,
                    geometry=shape,
                    attributes=attrs,
                    capture=capture,
                    actor=actor,
                )
                if target == "administrative_area"
                else None
            )
            obj, action, before, after = reconcile_map_record(
                model=TARGETS[target],
                namespace=namespace,
                record_id=identity,
                values=values,
                geometry=shape,
                canonical_id=canonical_id,
            )
            if target == "administrative_area":
                from ..models import AdministrativeAreaSourceAlias

                AdministrativeAreaSourceAlias.objects.filter(
                    source_namespace=namespace,
                    source_record_id=identity,
                    capture=capture,
                    active=True,
                ).update(canonical_revision=obj.revision)
            summary[action] += 1
            MapObservation.objects.create(
                **{target: obj},
                capture=capture,
                source_record_id=f"{target}:{identity}",
                source_url=url,
                raw_attributes=attrs,
                mapping_version=mapping_version or run.connector_version,
                record_sha256=hashlib.sha256(
                    json.dumps(
                        {"attributes": attrs, "geometry": json.loads(shape.geojson)},
                        sort_keys=True,
                    ).encode()
                ).hexdigest(),
                source_published_at=published,
                action=action,
                target_revision=obj.revision,
                before=before,
                after=after,
            )
        # Keep missing identities: absence in a map snapshot is not proof of demolition.
        run.status = "quarantined" if rejected else "succeeded"
        run.summary, run.finished_at = summary, timezone.now()
        run.save(update_fields=["status", "summary", "finished_at"])
    return run
