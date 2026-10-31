"""The API's direct reads of a source site, behind the collection switch (A25).

The manual connectors `maps/map_sources.py`, `maps/onwani.py` and
`sources/research_import.py` read reviewed public endpoints with the standard library,
outside the ingestion `SourceHTTP`, and so does the Sentinel-2 script
`scripts/acquire_reem_imagery.py` from its isolated Rasterio venv (A27). They open every
request here: the request and each redirect it follows are checked against
`collection_allowed` before they leave, so the switch of A22 stops these paths as it
stops the collectors. Replays of archived receipts never come here and stay exact. No
Django is needed, so protocol tests stay portable and the script imports this module
without the API environment.
"""

from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, build_opener

from .source_rights import collection_allowed


class CollectionForbidden(ValueError):
    """The site's terms forbid automated collection and the switch applies them."""


def collectable_url(url):
    if not collection_allowed(url):
        raise CollectionForbidden("Source terms forbid automated collection")
    return url


class _CheckedRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            collectable_url(newurl)
        except CollectionForbidden:
            fp.close()
            raise
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = build_opener(_CheckedRedirects)


def open_source(request, *, timeout):
    """The response to a source request, an HTTP error response included for its capture."""
    collectable_url(request.full_url)
    try:
        return OPENER.open(request, timeout=timeout)
    except HTTPError as exc:
        return exc
