from django.conf import settings
from django.core.checks import Error, register

from property_platform.object_storage.core import StorageConfig, StorageError


@register("media_storage")
def media_storage_configuration(app_configs, **kwargs):
    try:
        StorageConfig(**settings.MEDIA_STORAGE).validate()
    except StorageError, ValueError:
        return [
            Error(
                "Invalid media storage configuration.",
                hint="See MEDIA_STORAGE and docs/engineering/MEDIA_STORAGE.md; no cloud probe ran.",
                id="evidence.E001",
            )
        ]
    return []
