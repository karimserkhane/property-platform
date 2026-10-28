import os
from unittest.mock import patch

import pytest
from django.db import OperationalError, connection


def test_liveness_does_not_access_database(client):
    with patch(
        "property_platform.api.router.connection.cursor", side_effect=AssertionError("DB accessed")
    ):
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_unavailable_without_leaking_database_errors(client):
    with patch(
        "property_platform.api.router.connection.cursor",
        side_effect=OperationalError("private details"),
    ):
        response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "private details" not in response.content.decode()


def test_staff_admin_and_interactive_docs_are_not_exposed_in_non_debug_mode(client):
    assert client.get("/admin/").status_code == 404
    assert client.get("/api/v1/docs").status_code == 404


@pytest.mark.postgis
@pytest.mark.django_db
@pytest.mark.skipif(
    os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1", reason="PostGIS not enabled"
)
def test_readiness_uses_real_postgis(client):
    assert connection.vendor == "postgresql"
    with connection.cursor() as cursor:
        cursor.execute("SELECT ST_SRID(ST_SetSRID(ST_Point(54.4, 24.5), 4326))")
        assert cursor.fetchone()[0] == 4326
    assert client.get("/api/v1/health/ready").status_code == 200
