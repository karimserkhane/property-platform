"""The API's manual connectors follow the collection switch before any request (A25)."""

from io import BytesIO
from unittest.mock import patch
from urllib.request import HTTPRedirectHandler, Request

import pytest

from property_platform.modules.evidence import source_fetch
from property_platform.modules.evidence.maps import map_sources, onwani
from property_platform.modules.evidence.source_fetch import CollectionForbidden
from property_platform.modules.evidence.sources import research_import

REFERENCE = "https://reportagegroup.com/projects/residential-apartments/marlin/"
PATHS = {
    "map": lambda: map_sources.fetch_url(map_sources.OSM_URL, {"data": "[out:json];"}),
    "onwani": onwani.fetch,
    "reference": lambda: research_import.fetch_reference(REFERENCE),
}
HOSTS = {
    "map": "overpass-api.de",
    "onwani": "onwani.abudhabi.ae",
    "reference": "reportagegroup.com",
}


class Response(BytesIO):
    status = 200

    def __init__(self, url, payload):
        super().__init__(payload)
        self.url, self.headers = url, {}

    def geturl(self):
        return self.url


@pytest.mark.parametrize("enforced", [False, True])
@pytest.mark.parametrize("path", PATHS)
def test_manual_connectors_follow_the_collection_switch(
    path, enforced, enforce_rights, forbid_collection
):
    enforce_rights(collection=enforced, publication=False)
    forbid_collection(HOSTS[path])
    opened = []

    def answer(request, timeout):
        opened.append(request.full_url)
        return Response(request.full_url, b"{}")

    with patch.object(source_fetch.OPENER, "open", side_effect=answer):
        if enforced:
            with pytest.raises(CollectionForbidden, match="forbid"):
                PATHS[path]()
        else:
            payload, receipt = PATHS[path]()
            assert payload == b"{}" and receipt["http_status"] == 200
    assert len(opened) == (0 if enforced else 1)


@pytest.mark.parametrize("enforced", [False, True])
def test_redirects_follow_the_collection_switch(enforced, enforce_rights, forbid_collection):
    enforce_rights(collection=enforced, publication=False)
    forbid_collection("aldar.com")
    target = "https://www.aldar.com/en/projects/example"
    redirects = [h for h in source_fetch.OPENER.handlers if isinstance(h, HTTPRedirectHandler)]
    assert [type(handler) for handler in redirects] == [source_fetch._CheckedRedirects]
    body = BytesIO(b"moved")

    def follow():
        return redirects[0].redirect_request(Request(REFERENCE), body, 302, "Found", {}, target)

    if enforced:
        with pytest.raises(CollectionForbidden, match="forbid"):
            follow()
        assert body.closed
    else:
        assert follow().full_url == target and not body.closed
