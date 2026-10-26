"""Materialise complete public dashboard observations, without guessing property identity."""

import hashlib

from django.db import transaction
from django.utils import timezone

from ..models import (
    AdrecIndexObservation,
    AdrecMarketSnapshot,
    AdrecSaleObservation,
    Capture,
    IngestionRun,
    Source,
)
from ..runs import mark_failed
from . import adrec


def import_adrec(*, operation, scope, actor, acquisition):
    key, name, url, version = adrec.source_definition(operation, scope)
    source, _ = Source.objects.get_or_create(key=key, defaults={"name": name, "url": url})
    run = IngestionRun.objects.create(source=source, actor=actor, connector_version=version)

    def acquire(url, params):
        adrec.validate_request(operation, scope, url, params)
        payload, receipt = acquisition(url, params)
        capture = Capture.objects.create(
            run=run,
            payload=payload,
            byte_length=len(payload),
            content_sha256=hashlib.sha256(payload).hexdigest(),
            **receipt,
        )
        if receipt["http_status"] != 200:
            raise adrec.AdrecError("ADREC returned a non-success response")
        return payload, capture

    try:
        if operation == "adrec_sales":
            territory, start, end = adrec.sales_window(scope)
            pages, count = adrec.collect_sales(scope, acquire)
            with transaction.atomic():
                snapshot = AdrecMarketSnapshot.objects.create(
                    run=run,
                    dataset="sales",
                    territory=territory,
                    period_start=start,
                    period_end=end,
                    source_row_count=count,
                )
                observations = []
                for _, capture, rows in pages:
                    for index, row in enumerate(rows):
                        observations.append(
                            AdrecSaleObservation(
                                snapshot=snapshot,
                                capture=capture,
                                source_position=len(observations),
                                field_path=f"content[{index}]",
                                record_sha256=adrec.digest(row),
                                **adrec.sale_record(row, scope),
                            )
                        )
                AdrecSaleObservation.objects.bulk_create(observations, batch_size=500)
            run.summary = {
                "sales": count,
                "snapshot_id": str(snapshot.pk),
                "from": str(start),
                "to": str(end),
            }
            run.status = "succeeded"
        else:
            staged, conflicts = [], {}
            for kind, endpoint in adrec.INDICES.items():
                payload, capture = acquire(endpoint, adrec.index_params())
                rows, conflict_count = adrec.index_records(payload)
                conflicts[kind] = conflict_count
                staged.append((kind, capture, rows))
            with transaction.atomic():
                snapshot = AdrecMarketSnapshot.objects.create(
                    run=run,
                    dataset="indices",
                    territory="abu-dhabi",
                    source_row_count=sum(len(rows) for _, _, rows in staged),
                )
                observations = []
                for kind, capture, rows in staged:
                    for index, (values, row) in enumerate(rows):
                        observations.append(
                            AdrecIndexObservation(
                                snapshot=snapshot,
                                capture=capture,
                                source_position=index,
                                field_path=f"[{index}]",
                                record_sha256=adrec.digest(row),
                                kind=kind,
                                usable=not conflicts[kind],
                                review_reason="Indistinguishable series contain conflicting values"
                                if conflicts[kind]
                                else "",
                                **values,
                            )
                        )
                AdrecIndexObservation.objects.bulk_create(observations, batch_size=500)
            run.summary = {
                "observations": len(observations),
                "conflicting_series": conflicts,
                "snapshot_id": str(snapshot.pk),
            }
            run.status = "quarantined" if any(conflicts.values()) else "succeeded"
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "summary", "finished_at"])
        return run
    except Exception as exc:
        mark_failed(run, exc)
        raise
