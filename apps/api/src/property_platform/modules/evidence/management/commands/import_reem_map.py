from django.core.management.base import BaseCommand, CommandError

from property_platform.modules.evidence.map_import import import_map_layer


class Command(BaseCommand):
    help = (
        "Acquire official district/sectors/streets and OSM buildings/places directly into PostGIS."
    )

    def add_arguments(self, parser):
        parser.add_argument("--actor", required=True)
        parser.add_argument(
            "--receipt",
            help="Operator-provided OSM receipt bundle, replayed without claiming a new fetch",
        )
        parser.add_argument(
            "--layer", choices=["all", "district", "community", "street", "osm"], default="all"
        )

    def handle(self, *args, **options):
        import base64
        import json
        from datetime import datetime
        from pathlib import Path
        from urllib.parse import parse_qs, urlparse

        from django.utils import timezone

        from property_platform.modules.evidence import map_sources as protocol

        actor = options["actor"].strip()
        if not actor or len(actor) > 160:
            raise CommandError("Actor must contain 1–160 characters")
        layers = (
            ["district", "community", "street", "osm"]
            if options["layer"] == "all"
            else [options["layer"]]
        )
        replay = None
        if options["receipt"]:
            if layers != ["osm"]:
                raise CommandError("Receipt replay requires --layer osm")
            path = Path(options["receipt"])
            if path.stat().st_size > 24 * 1024 * 1024:
                raise CommandError("Receipt bundle too large")
            bundle = json.loads(path.read_text(encoding="utf-8"))
            receipt = bundle["receipt"]
            if set(receipt) - {
                "url",
                "http_status",
                "fetched_started_at",
                "fetched_at",
                "etag",
                "last_modified_raw",
                "acquisition_method",
                "timestamp_basis",
            }:
                raise CommandError("Unexpected receipt fields")
            parsed = urlparse(receipt["url"])
            if f"{parsed.scheme}://{parsed.netloc}{parsed.path}" not in (
                protocol.OSM_URL,
                protocol.OSM_MIRROR,
            ) or parse_qs(parsed.query).get("data") != [protocol.OSM_QUERY]:
                raise CommandError("Receipt does not match the fixed OSM acquisition")
            for key in ("fetched_started_at", "fetched_at"):
                receipt[key] = datetime.fromisoformat(receipt[key]) if receipt.get(key) else None
            if receipt["fetched_at"] is None or receipt["fetched_at"].tzinfo is None:
                raise CommandError("Receipt time must be timezone-aware")
            if (
                receipt["http_status"] != 200
                or receipt["fetched_at"] > timezone.now()
                or receipt.get("timestamp_basis")
                not in ("collector_clock", "local_receipt_file_mtime")
                or (
                    receipt["fetched_started_at"] is not None
                    and (
                        receipt["fetched_started_at"].tzinfo is None
                        or receipt["fetched_started_at"] > receipt["fetched_at"]
                    )
                )
            ):
                raise CommandError("Invalid receipt status or chronology")
            receipt["acquisition_method"] = "manual_receipt_replay"
            replay = (base64.b64decode(bundle["payload_base64"], validate=True), receipt)
            if len(replay[0]) > protocol.MAX_BYTES:
                raise CommandError("Receipt payload too large")
        for layer in layers:
            try:
                run = import_map_layer(layer=layer, actor=actor, replay=replay)
            except Exception as exc:
                raise CommandError(
                    f"{layer}: {type(exc).__name__}; previous data preserved"
                ) from exc
            self.stdout.write(f"{layer}: {run.id} {run.status} {run.summary}")
