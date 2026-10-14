"""Package a manually obtained official ADEK file, retaining an approximate artifact time."""

import argparse
import base64
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from property_platform.modules.evidence import abu_dhabi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.input.stat().st_size > abu_dhabi.MAX_BYTES:
        raise ValueError("Source archive exceeds budget")
    payload = args.input.read_bytes()
    abu_dhabi.parse("abu-dhabi:schools", payload)
    receipt = {
        "scope": "abu-dhabi:schools",
        "url": abu_dhabi.FEEDS["schools"].url,
        "http_status": 200,
        "payload_base64": base64.b64encode(payload).decode(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "fetched_at": datetime.fromtimestamp(
            args.input.stat().st_mtime, tz=UTC
        ).isoformat(),
        "timestamp_basis": "artifact_filesystem_time",
        "acquisition_method": "manual_archive_import",
    }
    abu_dhabi.archive_response("abu-dhabi:schools", receipt)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt), encoding="utf-8", newline="\n")
    print("Prepared manual school receipt; source publication time remains unknown.")


if __name__ == "__main__":
    main()
