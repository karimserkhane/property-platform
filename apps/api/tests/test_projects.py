import pytest
from django.test import override_settings


@pytest.mark.parametrize(("debug", "preview"), [(False, True), (True, False), (False, False)])
def test_project_details_require_local_preview_opt_in(client, debug, preview):
    with override_settings(DEBUG=debug, PROPERTY_PLATFORM_PARCEL_PREVIEW=preview):
        response = client.get("/api/v1/preview/projects/park-view")
    assert response.status_code == 403
    assert response.json() == {"code": "preview_disabled"}


@pytest.mark.parametrize("slug", ["PARK-VIEW", "park_view", "-park-view", "a" * 101])
def test_invalid_project_slug_is_rejected_before_database_access(client, slug):
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get(f"/api/v1/preview/projects/{slug}")
    assert response.status_code == 404
    assert response.json() == {"code": "not_found"}
