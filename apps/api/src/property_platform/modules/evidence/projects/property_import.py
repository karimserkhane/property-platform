"""Explicit source-identity review, never a name or proximity identity merge."""

import hashlib
import html
import json
import re
from pathlib import Path

from django.db import connection, transaction
from django.utils import timezone

from property_platform.modules.catalog.models import Building, Place

from ..collection_profiles import DEFAULT_TERRITORY, collection_for
from ..models import Capture, IngestionRun, PropertyMedia, PropertyPresentation, Source
from ..source_withdrawals import is_withdrawn
from .property_protocol import safe_url, validate_photo, validate_receipts

ROOT = Path(__file__).parent.parent
VERSION = "property-presentation-review-v1"
TARGETS = {"building": Building, "place": Place}


def registry(territory=DEFAULT_TERRITORY):
    profile = collection_for(territory)
    return (
        json.loads((ROOT / profile.presentation_registry).read_text(encoding="utf-8")),
        json.loads((ROOT / profile.media_registry).read_text(encoding="utf-8")),
    )


def import_presentations(receipt_rows, *, actor, profiles=None, photos=None):
    if not actor.strip() or len(actor) > 160:
        raise ValueError("Valid actor required")
    if profiles is None or photos is None:
        profiles, photos = registry()
    # A withdrawn site's profile replays from batches that hold it; new collections no
    # longer contain it, nor its photograph (A19).
    present = {row.get("url") for row in receipt_rows if isinstance(row, dict)}
    profiles = [
        row
        for row in profiles
        if row["source_url"] in present or not is_withdrawn(row["source_url"])
    ]
    allowed = {row["source_url"] for row in profiles}
    for row in profiles:
        if row.get("photo_key"):
            photo = photos[row["photo_key"]]
            allowed.update((photo["source_url"], photo["image_url"]))
    receipts = validate_receipts(receipt_rows, allowed)
    identities = []
    for row in profiles:
        if (
            row["target"] not in TARGETS
            or not safe_url(row["website_url"])
            or not safe_url(row["source_url"])
        ):
            raise ValueError("Unexpected property identity or URL")
        model = TARGETS[row["target"]]
        obj = model.objects.get(
            active=True, source_namespace=row["namespace"], source_record_id=row["record_id"]
        )
        text = html.unescape(
            receipts[row["source_url"]]["payload"].decode("utf-8", errors="replace")
        ).lower()
        if any(term.lower() not in text for term in row["required_terms"]):
            raise ValueError("Reviewed claims no longer match their source")
        plain_text = " ".join(re.sub(r"<[^>]+>", " ", text).split())
        if row["developer_name"] and row["developer_name"].lower() not in plain_text:
            raise ValueError("Developer name is not present in its captured source")
        if row.get("photo_key"):
            validate_photo(photos[row["photo_key"]], receipts)
        identities.append((row, obj))
    # Validate the entire batch before persisting anything; never mutate catalogue identities.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(716548220)")
        output = []
        for row, obj in identities:
            source, _ = Source.objects.get_or_create(
                key="property:" + hashlib.sha256(row["source_url"].encode()).hexdigest()[:40],
                defaults={"name": row["publisher_name"], "url": row["source_url"]},
            )
            run = IngestionRun.objects.create(
                source=source, actor=actor.strip(), connector_version=VERSION
            )

            def capture(url, parent=None, acquisition_run=run):
                receipt = receipts[url]
                return Capture.objects.create(
                    run=acquisition_run,
                    parent_capture=parent,
                    url=url,
                    payload=receipt["payload"],
                    byte_length=len(receipt["payload"]),
                    content_sha256=receipt["sha256"],
                    http_status=200,
                    fetched_started_at=receipt["fetched_started_at"],
                    fetched_at=receipt["fetched_at"],
                    acquisition_method="manual_receipt_replay",
                    timestamp_basis="receipt_collector_clock",
                )

            presentation = PropertyPresentation.objects.create(
                **{row["target"]: obj},
                capture=capture(row["source_url"]),
                **{
                    key: row[key]
                    for key in (
                        "display_name",
                        "publisher_name",
                        "developer_name",
                        "website_url",
                        "summary",
                        "language",
                    )
                },
                review_version=VERSION,
            )
            if row.get("photo_key"):
                photo = photos[row["photo_key"]]
                licence_capture = capture(photo["source_url"])
                PropertyMedia.objects.create(
                    presentation=presentation,
                    capture=capture(photo["image_url"], licence_capture),
                    licence_capture=licence_capture,
                    **{
                        key: photo[key]
                        for key in (
                            "source_url",
                            "author",
                            "licence_code",
                            "licence_url",
                            "caption",
                            "language",
                            "taken_on",
                            "mime_type",
                        )
                    },
                )
            run.status, run.finished_at = "succeeded", timezone.now()
            run.summary = {
                "presentation_id": presentation.pk,
                "target": row["target"],
                "identity": str(obj.pk),
                "basis": "reviewed_exact_provider_identity",
            }
            run.save(update_fields=["status", "finished_at", "summary"])
            output.append(presentation)
    return output
