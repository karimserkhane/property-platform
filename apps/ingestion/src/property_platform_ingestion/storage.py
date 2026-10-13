"""Private source receipts, not database dumps; exact receipts survive a task retry."""

import json
import os
import re
import tempfile
from pathlib import Path

MAX_RECEIPT = 32 * 1024 * 1024


def _read_receipt(path):
    if path.is_symlink() or path.stat().st_size > MAX_RECEIPT:
        raise ValueError("Invalid stored receipt")
    with path.open("rb") as handle:
        content = handle.read(MAX_RECEIPT + 1)
    if len(content) > MAX_RECEIPT:
        raise ValueError("Stored receipt exceeds its byte budget")
    return json.loads(content)


def stored_property_receipt(root: Path, execution_key: str, collect):
    if not re.fullmatch(r"[0-9a-f]{64}", execution_key):
        raise ValueError("Invalid receipt identity")
    root = root.resolve()
    folder = (root / "receipts").resolve()
    if folder.parent != root:
        raise ValueError("Receipt storage escapes its configured root")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{execution_key}.json"
    if path.exists():
        return _read_receipt(path)
    rows = collect()
    encoded = json.dumps(rows).encode()
    if len(encoded) > MAX_RECEIPT:
        raise ValueError("Property acquisition exceeds its receipt budget")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=folder, prefix="receipt-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # Publish without overwriting a checkpoint another attempt won first.
            # Both named Docker volumes and the local NTFS workspace support links.
            os.link(temporary, path)
        except FileExistsError:
            pass
        return _read_receipt(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
