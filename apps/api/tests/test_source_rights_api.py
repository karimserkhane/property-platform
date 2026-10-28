from django.test import override_settings

from property_platform.modules.evidence.source_rights import source_rights


def test_source_rights_list_the_reviewed_registry(client):
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get("/api/v1/preview/source-rights")
    assert response.status_code == 200
    items = response.json()["items"]
    registry = source_rights()
    assert [item["host"] for item in items] == [row["host"] for row in registry]
    for item, row in zip(items, registry, strict=True):
        # Who reviewed and why stay in the registry; readers get rights and links.
        assert "reviewed_by" not in item and "basis" not in item
        assert item["publisher"] == row["publisher"]
        assert item["licence"] == row["licence"]
        assert item["collection"] == row["collection"]
        assert item["publication"] == row["publication"]
        assert item["reviewed_on"] == row["reviewed_on"]
        assert item["licence_url"] == (row["licence_url"] or None)
        assert item["terms_url"] == (row["terms_url"] or None)
        assert item["attribution"] == (row["attribution"] or None)
