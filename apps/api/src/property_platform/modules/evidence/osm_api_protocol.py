"""Portable OSM XML validation for the reviewed one-off Saadiyat windows."""

import math
from xml.etree import ElementTree

from .collection_profiles import collection_for
from .onwani import SourceError

URL = "https://api.openstreetmap.org/api/0.6/map"
VERSION = "osm-api-bootstrap-v1"
MAX_BYTES = 16 * 1024 * 1024


def boxes(territory):
    p = collection_for(territory)
    if territory != "saadiyat-island":
        raise ValueError("OSM API bootstrap is reviewed only for Saadiyat")
    w, s, e, n = p.osm_bounds
    x, y = round((w + e) / 2, 8), round((s + n) / 2, 8)
    return tuple(
        {"bbox": ",".join(map(str, b))}
        for b in ((w, s, x, y), (x, s, e, y), (w, y, x, n), (x, y, e, n))
    )


def decode(payload):
    if len(payload) > MAX_BYTES:
        raise SourceError("OSM XML exceeds its budget")
    try:
        # The reviewed API emits UTF-8. Alternate encodings must not bypass
        # the declaration guard before ElementTree processes the document.
        text = payload.decode("utf-8")
        if "\x00" in text or "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            raise SourceError("OSM XML contains forbidden declarations or encoding")
        root = ElementTree.fromstring(text)
        if root.tag != "osm" or root.get("version") != "0.6" or len(root) > 65000:
            raise SourceError("Unexpected OSM XML protocol or element budget")
        nodes, elements, seen = {}, [], set()
        for node in root.findall("node"):
            identity = int(node.attrib["id"])
            point = {"lat": float(node.attrib["lat"]), "lon": float(node.attrib["lon"])}
            if (
                identity in nodes
                or identity <= 0
                or not (
                    math.isfinite(point["lat"])
                    and math.isfinite(point["lon"])
                    and -90 <= point["lat"] <= 90
                    and -180 <= point["lon"] <= 180
                )
            ):
                raise SourceError("Invalid OSM node identity or coordinates")
            nodes[identity] = point
        for row in root:
            if row.tag not in {"node", "way", "relation"}:
                continue
            identity = (row.tag, int(row.attrib["id"]))
            if identity in seen or identity[1] <= 0:
                raise SourceError("Duplicate OSM source identity")
            seen.add(identity)
            tags = {t.attrib["k"]: t.attrib["v"] for t in row.findall("tag")}
            if not (
                tags.get("building")
                or (
                    tags.get("name") and any(tags.get(k) for k in ("highway", "amenity", "leisure"))
                )
            ):
                continue
            e = {
                "type": row.tag,
                "id": identity[1],
                "version": int(row.attrib["version"]),
                "timestamp": row.attrib["timestamp"],
                "tags": tags,
            }
            if row.tag == "node":
                e.update(nodes[identity[1]])
            elif row.tag == "way":
                # Full referenced-node coverage is required; no invented polygon closure.
                e["geometry"] = [nodes[int(nd.attrib["ref"])] for nd in row.findall("nd")]
            # Incomplete relations have no invented centre; the shared parser quarantines them.
            elements.append(e)
        if not 1 <= len(elements) <= 20000:
            raise SourceError("Unexpected OSM materialisation budget")
        return {"source_format": "osm_api_xml", "elements": elements}
    except (ElementTree.ParseError, KeyError, TypeError, ValueError) as exc:
        raise SourceError("Invalid or incomplete OSM XML") from exc
