"""Conservative display-only suppression; source identities and observations stay intact."""

import math
import unicodedata


def distinct_places(rows):
    def label(row):
        return "".join(
            c for c in unicodedata.normalize("NFKC", row["name"]).casefold() if c.isalnum()
        )

    # Existing locally reviewed/OSM points lead; Overture supplies missing destinations.
    priority = sorted(rows, key=lambda row: row["source_namespace"].startswith("overture:"))
    kept, labels = [], {}
    for row in priority:
        key = (label(row), row["kind"])
        point = row["geometry"]["coordinates"]
        duplicate = False
        if key[0] and row["source_namespace"].startswith("overture:"):
            for previous in labels.get(key, []):
                other = previous["geometry"]["coordinates"]
                x = math.radians(point[0] - other[0]) * math.cos(math.radians(point[1]))
                y = math.radians(point[1] - other[1])
                if previous["source_namespace"] != row["source_namespace"] and (
                    math.hypot(x, y) * 6371000 <= 15
                ):
                    duplicate = True
                    break
        if not duplicate:
            kept.append(row)
            labels.setdefault(key, []).append(row)
    retained = {str(row["id"]) for row in kept}
    return [row for row in rows if str(row["id"]) in retained]
