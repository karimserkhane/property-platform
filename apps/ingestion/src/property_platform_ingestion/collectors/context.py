"""Acquire registered public feeds before the SQL transaction; preserve exact bytes."""

from property_platform.modules.evidence import abu_dhabi

from .snapshots import ReplayFetcher, _params


def precollect_context(transport, scope):
    abu_dhabi.feed_for(scope)
    replay = ReplayFetcher()

    def acquire(url, params):
        abu_dhabi.validate_request(scope, url, params)

        def collect():
            result = transport.fetch(url, max_bytes=abu_dhabi.MAX_BYTES)
            if result.http_status != 200:
                raise abu_dhabi.ContextError("Public context feed returned a non-success response")
            return result.payload, result.capture_receipt()

        return replay._acquire(("map", url, _params(params)), collect)

    abu_dhabi.collect(scope, acquire)
    return replay


def replay_school_archive(scope, receipt):
    payload, proof = abu_dhabi.archive_response(scope, receipt)
    abu_dhabi.parse(scope, payload)
    replay = ReplayFetcher()
    replay._acquire(("map", proof["url"], _params({})), lambda: (payload, proof))
    return replay
