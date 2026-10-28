"""Provider-specific, inert parsers for declared project points, never parcel ownership."""

import html
import json
import math
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse


class _MapElements(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag in {"div", "iframe"}:
            self.nodes.append((tag, dict(attrs)))


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
        if set(fields) == {"latitude", "longitude", "title"} and (
            name_matches(fields["title"], title) or name_matches(title, fields["title"])
        ):
            candidates.append(
                (
                    fields["title"],
                    float(fields["latitude"]),
                    float(fields["longitude"]),
                    "publisher_map",
                )
            )
    elif parsed.hostname in {"saasproperties.com", "www.saasproperties.com"}:
        for tag, attrs in _MapElements(text).nodes:
            if tag != "iframe":
                continue
            embed = urlparse(attrs.get("src", ""))
            if embed.hostname != "www.google.com" or embed.path != "/maps/embed":
                continue
            pb = parse_qs(embed.query).get("pb", [""])[0]
            # The viewport !2d/!3d pair is the camera, not the project pin.
            position = re.search(r"!8m2!3d([\d.]+)!4d([\d.]+)", pb)
            label = re.search(r"!2s([^!]+)", pb)
            if position and label and name_matches(title, unquote(label[1])):
                candidates.append(
                    (title, float(position[1]), float(position[2]), "publisher_embedded_pin")
                )
    elif parsed.hostname == "bloomholding.com" and parsed.path.startswith(
        "/what-we-do/properties/"
    ):
        for _, attrs in _MapElements(text).nodes:
            if attrs.get("id") != "map_canvas":
                continue
            location = attrs.get("data-location", "").split(",")
            if len(location) == 2:
                try:
                    candidates.append(
                        (title, float(location[0]), float(location[1]), "publisher_map")
                    )
                except ValueError:
                    continue
    elif parsed.hostname == "object-1.com" and parsed.path.startswith("/project/"):
        for _, attrs in _MapElements(text).nodes:
            try:
                markers = json.loads(attrs.get("data-markers", "[]"))
            except ValueError, TypeError:
                continue
            if not isinstance(markers, list):
                continue
            for marker in markers[:100]:
                if (
                    isinstance(marker, dict)
                    and marker.get("type") == "object"
                    and name_matches(title, str(marker.get("label", "")))
                ):
                    try:
                        candidates.append(
                            (title, float(marker["lat"]), float(marker["lng"]), "publisher_map")
                        )
                    except KeyError, ValueError, TypeError:
                        continue
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
