"""Canonical commercial identity mutations; their evidence is committed by the caller."""

from django.db import connection

from .models import Developer, Project
from .territories import TERRITORY_BY_ID


def reconcile_project(definition):
    if not connection.in_atomic_block:
        raise ValueError("Project identity changes require their evidence transaction")
    if definition["territory_id"] not in TERRITORY_BY_ID:
        raise ValueError("Unknown project territory")
    developer_data = definition["developer"]
    developer, _ = Developer.objects.get_or_create(
        key=developer_data["key"],
        defaults={key: developer_data[key] for key in ("name", "website_url")},
    )
    if (developer.name, developer.website_url) != (
        developer_data["name"],
        developer_data["website_url"],
    ):
        raise ValueError("Developer identity changed; a reviewed identity change is required")
    values = {key: definition[key] for key in ("name", "territory_id", "website_url")}
    project, _ = Project.objects.get_or_create(
        slug=definition["slug"], defaults={**values, "developer": developer}
    )
    if project.developer_id != developer.id or any(
        getattr(project, key) != value for key, value in values.items()
    ):
        raise ValueError("Project identity changed; a reviewed identity change is required")
    return project
