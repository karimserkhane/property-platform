"""Provider-specific, inert parsers for declared project points, never parcel ownership."""

import html
import json
import math
import re
from urllib.parse import urlparse


def page_metadata(payload):
    text = payload.decode("utf-8", errors="replace")
    match = re.search(r"<title\b[^>]*>(.*?)</title>", text, re.I | re.S)
    title = html.unescape(re.sub(r"<[^>]+>", "", match[1])).strip()[:255] if match else ""
    markers = re.findall(r'data-lat="([\d.]+)"\s+data-lng="([\d.]+)"', text)
    return title, markers


def name_matches(name, title):
    words = set(re.findall(r"[a-z0-9]+", name.lower())) - {
        "al",
        "reem",
        "island",
        "abu",
        "dhabi",
        "by",
        "reportage",
        "properties",
        "united",
        "arab",
        "emirates",
        "uae",
    }
    return bool(words) and words.issubset(set(re.findall(r"[a-z0-9]+", title.lower())))


def project_marker(payload, url, title):
    parsed = urlparse(url)
    text = payload.decode("utf-8", errors="replace")
    candidates = []
    if parsed.hostname == "reportagegroup.com" and parsed.path.startswith("/projects/"):
        for match in re.finditer(
            r'<div\b[^>]*data-lat="([\d.]+)"\s+data-lng="([\d.]+)"[^>]*>\s*<p[^>]*>(.*?)</p>',
            text,
            re.I | re.S,
        ):
            name = html.unescape(re.sub(r"<[^>]+>", "", match[3])).strip()
            if name_matches(re.split(r"\s+by\s+Reportage", name, flags=re.I)[0], title):
                candidates.append(
                    (
                        title.split(" - Reportage")[0],
                        float(match[1]),
                        float(match[2]),
                        "publisher_map",
                    )
                )
    elif parsed.hostname in ("www.modon.com", "modon.com") and parsed.path.startswith(
        "/real-estate/"
    ):
        fields = {}
        for match in re.finditer(
            r'<input\b[^>]*id="map-(latitude|longitude|title)"[^>]*value="([^"]*)"', text, re.I
        ):
            fields[match[1]] = html.unescape(match[2])
        if set(fields) == {"latitude", "longitude", "title"} and name_matches(
            fields["title"], title
        ):
            candidates.append(
                (
                    fields["title"],
                    float(fields["latitude"]),
                    float(fields["longitude"]),
                    "publisher_map",
                )
            )
    elif (
        parsed.hostname in ("jre.ae", "rendr.ae") and parsed.path.startswith("/projects/")
    ) or parsed.hostname in (
        "rotanaresidences-alreem.rdhuae.com",
        "radissonresidences-alreem.rdhuae.com",
    ):

        def walk(value, depth=0):
            if depth > 20:
                return
            if isinstance(value, list):
                for child in value[:500]:
                    walk(child, depth + 1)
            elif isinstance(value, dict):
                geo, name = value.get("geo"), value.get("name")
                if (
                    value.get("@type") in ("ApartmentComplex", "RealEstateListing")
                    and isinstance(name, str)
                    and name_matches(name, title)
                    and isinstance(geo, dict)
                    and geo.get("@type") == "GeoCoordinates"
                    and (not value.get("url") or value["url"].rstrip("/") == url.rstrip("/"))
                ):
                    candidates.append(
                        (
                            name,
                            float(geo["latitude"]),
                            float(geo["longitude"]),
                            "declared_jsonld_project",
                        )
                    )
                for child in list(value.values())[:500]:
                    walk(child, depth + 1)

        for match in re.finditer(
            r'<script\b[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', text, re.I | re.S
        ):
            try:
                walk(json.loads(match[1]))
            except ValueError, KeyError, TypeError, RecursionError:
                continue
    unique = set(candidates)
    if len(unique) != 1:
        return None
    name, lat, lon, method = unique.pop()
    if not (
        math.isfinite(lat) and math.isfinite(lon) and 24.4 <= lat <= 24.6 and 54.3 <= lon <= 54.55
    ):
        return None
    return {"name": name[:255], "lat": lat, "lon": lon, "method": method}
