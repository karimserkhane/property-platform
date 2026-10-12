from liwa.modules.catalog.map_queries import map_rows
from liwa.modules.evidence.queries import map_provenances


def map_context(bbox):
    result = {}
    for target in ("street", "building", "place", "administrative_area"):
        rows, truncated = map_rows(target, bbox)
        sources = map_provenances(target, [row["id"] for row in rows])
        result[target] = {"type": "FeatureCollection", "truncated": truncated, "features": []}
        for row in rows:
            identity = str(row.pop("id"))
            source = sources.get(identity)
            if source is None:
                continue
            geometry = row.pop("geometry")
            row.pop("source_namespace")
            result[target]["features"].append(
                {
                    "type": "Feature",
                    "id": identity,
                    "geometry": geometry,
                    "properties": {"id": identity, **row, "source": source},
                }
            )
    return result
