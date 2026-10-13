"""Public, bounded HTTPS collection before Django opens the write transaction."""

from urllib.parse import urlencode

from property_platform.modules.evidence import adrec

from .snapshots import ReplayFetcher, _params


def precollect_adrec(transport, operation, scope):
    replay = ReplayFetcher()

    def acquire(url, params):
        adrec.validate_request(operation, scope, url, params)

        def collect():
            result = transport.fetch(
                url + "?" + urlencode(params), allowed_base=url, max_bytes=adrec.MAX_BYTES
            )
            if result.http_status != 200:
                raise adrec.AdrecError("ADREC returned a non-success response")
            return result.payload, result.capture_receipt()

        return replay._acquire(("map", url, _params(params)), collect)

    if operation == "adrec_sales":
        adrec.collect_sales(scope, acquire)
    else:
        for endpoint in adrec.INDICES.values():
            payload, _ = acquire(endpoint, adrec.index_params())
            adrec.index_records(payload)
    return replay
