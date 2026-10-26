"""Statements a published project dossier makes, each with the evidence that backs it (E01).

Pure functions over `project_detail` output: the index only ever holds what the site
publishes, never raw captures or operator details. A statement keeps the original text
when the dossier carries it; otherwise the published values are joined, never rephrased.
See docs/engineering/EVIDENCE_SEARCH.md.
"""

import hashlib
import json
import re
import unicodedata

KINDS = (
    "summary",
    "handover",
    "programme_total",
    "typologies",
    "amenity",
    "declared_progress",
    "registration",
    "component_of",
    "has_component",
)
# Arabic letters folded to their usual spelling variants; tatweel is decoration only.
_ARABIC_FOLDS = str.maketrans({"ة": "ه", "ى": "ي", "ـ": None})
# Han and kana are written without spaces: each character is its own search term.
_UNSPACED = re.compile(r"([぀-ヿ㐀-䶿一-鿿豈-﫿])")
_WORD = re.compile(r"[^\W_]+")


def normalize(text):
    """Search form of a text: no accents or Arabic diacritics, case folded, words only."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    bare = "".join(char for char in decomposed if not unicodedata.combining(char))
    folded = unicodedata.normalize("NFC", bare).casefold().translate(_ARABIC_FOLDS)
    return " ".join(_WORD.findall(_UNSPACED.sub(r" \1 ", folded)))


def _source(source, fallback_language):
    return {
        "source_url": source.get("url") or "",
        "source_name": source.get("name") or "",
        "source_kind": source.get("kind") or "",
        "content_sha256": source.get("content_sha256") or "",
        "evidence_pointer": source.get("evidence_pointer") or "",
        "retrieved_at": source.get("retrieved_at"),
        "language": source.get("language") or fallback_language,
    }


def _joined(pairs):
    return "; ".join(f"{label}: {value}" for label, value in pairs if value not in (None, ""))


def _claim(dossier, kind, path, text, source, terms=()):
    if not text or not source or source.get("historical") or not source.get("url"):
        return None
    row = {"kind": kind, "path": path, "text": text, **_source(source, dossier["language"])}
    identity = [
        dossier["slug"],
        kind,
        path,
        text,
        row["source_url"],
        row["content_sha256"],
        row["evidence_pointer"],
        sorted(terms),
    ]
    row["claim_key"] = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, default=str).encode()
    ).hexdigest()
    row["search_text"] = normalize(" ".join([text, *terms]))
    return row


def _relation(dossier, kind, relation):
    source = {
        "url": relation["source_url"],
        "retrieved_at": relation["retrieved_at"],
        "evidence_pointer": "reviewed_project_relation",
    }
    text = _joined(
        (
            ("project", relation["name"]),
            ("component", relation["component"]),
            ("basis", relation["basis"]),
        )
    )
    return _claim(dossier, kind, f"{kind}:{relation['slug']}", text, source, (relation["slug"],))


def claims_from_dossier(dossier):
    """Indexed statements of one published dossier, in a stable order."""
    rows = []
    rows.append(
        _claim(
            dossier,
            "summary",
            "summary",
            dossier.get("summary"),
            dossier.get("summary_source") or {},
        )
    )
    for kind in ("handover", "programme_total"):
        fact = dossier.get(kind) or {}
        rows.append(_claim(dossier, kind, kind, fact.get("original_text"), fact.get("source")))
    # Typologies read from one original text share it: one statement per text.
    typologies = {}
    for item in dossier.get("typologies") or []:
        source = item.get("source") or {}
        key = (source.get("content_sha256"), source.get("evidence_pointer"), item["original_text"])
        typologies.setdefault(key, (item, set()))[1].update(
            str(value) for value in (item.get("property_type"), item.get("bedrooms")) if value
        )
    for item, terms in typologies.values():
        pointer = (item.get("source") or {}).get("evidence_pointer") or ""
        rows.append(
            _claim(
                dossier,
                "typologies",
                f"typologies:{pointer}",
                item["original_text"],
                item.get("source"),
                terms,
            )
        )
    for item in dossier.get("amenities") or []:
        rows.append(
            _claim(
                dossier,
                "amenity",
                f"amenity:{item['code']}",
                item.get("original_text"),
                item.get("source"),
                (item["code"].replace("_", " "), item.get("label") or ""),
            )
        )
    progress = dossier.get("declared_progress") or {}
    rows.append(
        _claim(
            dossier,
            "declared_progress",
            "declared_progress",
            _joined(
                (
                    ("register_status", progress.get("register_status")),
                    ("progress_percent", progress.get("progress_percent")),
                    ("progress_inspected_on", progress.get("progress_inspected_on")),
                )
            ),
            progress.get("source"),
        )
    )
    reading = (dossier.get("verification") or {}).get("latest_reading") or {}
    rows.append(
        _claim(
            dossier,
            "registration",
            "verification.latest_reading",
            _joined(
                (
                    ("registration_number", reading.get("registration_number")),
                    ("permit_number", reading.get("permit_number")),
                    ("register_status", reading.get("register_status")),
                    ("registered_on", reading.get("registered_on")),
                    ("developer_licence", reading.get("developer_licence")),
                    ("sold", reading.get("sold_original")),
                )
            ),
            reading.get("source"),
        )
    )
    if dossier.get("parent"):
        rows.append(_relation(dossier, "component_of", dossier["parent"]))
    for component in dossier.get("components") or []:
        rows.append(_relation(dossier, "has_component", component))
    return [row for row in rows if row]


def project_terms(dossier):
    """Search form of the project's identity, which every statement is read under."""
    developer = (dossier.get("developer") or {}).get("name") or ""
    return normalize(" ".join([dossier["name"], developer, dossier["slug"].replace("-", " ")]))


def query_terms(query, limit=12):
    """Prefix terms of a free-text query, safe to pass to `to_tsquery`."""
    terms = normalize(query).split()[:limit]
    return " & ".join(f"{term}:*" for term in terms)
