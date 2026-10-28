from django.apps import AppConfig


class EvidenceConfig(AppConfig):
    name = "property_platform.modules.evidence"
    label = "evidence"

    def ready(self):
        from . import checks  # noqa: F401
