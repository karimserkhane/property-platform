"""Collect only reviewed project HTML/terms; linked binaries are never fetched."""

import json

from property_platform.modules.evidence.projects.project_protocol import (
    MAX_CAPTURE_BYTES,
    MAX_PROJECT_RECEIPT_BYTES,
    extract_project_source,
    project_urls,
    validate_project_receipts,
)

from .http import AcquisitionError, SourceHTTP


def collect_project_receipts(
    client: SourceHTTP, projects, *, max_receipt_bytes=MAX_PROJECT_RECEIPT_BYTES
):
    urls = project_urls(projects)
    if (
        type(max_receipt_bytes) is not int
        or not 1 <= max_receipt_bytes <= MAX_PROJECT_RECEIPT_BYTES
    ):
        raise AcquisitionError("Invalid project receipt batch byte budget")
    receipts, size = [], 2
    for url in urls:
        receipt = client.fetch(url, max_bytes=MAX_CAPTURE_BYTES).property_receipt()
        size += len(json.dumps(receipt).encode("utf-8")) + (2 if receipts else 0)
        if size > max_receipt_bytes:
            raise AcquisitionError("Project acquisition exceeds its receipt batch byte budget")
        receipts.append(receipt)
    verified = validate_project_receipts(receipts, projects)
    for project in projects:
        for source in project["sources"]:
            extract_project_source(project, source, verified[source["url"]])
    return receipts
