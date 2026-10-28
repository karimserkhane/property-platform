"""Guards shared by every local preview router; see `router.py` for their registration."""

from functools import wraps

from django.conf import settings
from ninja import Status


class TerritoryNotConfigured(LookupError):
    """Answered as 409 `territory_not_configured` by the API exception handler."""


def enabled():
    return settings.DEBUG and getattr(settings, "PROPERTY_PLATFORM_PARCEL_PREVIEW", False)


def preview_only(view):
    """Answer 403 `preview_disabled` before the view runs while the preview is off."""

    @wraps(view)
    def guarded(request, *args, **kwargs):
        if not enabled():
            return Status(403, {"code": "preview_disabled"})
        return view(request, *args, **kwargs)

    return guarded


def territory_profile(territory):
    """Collection profile of an optional territory filter; None means every territory."""
    if not territory:
        return None
    from property_platform.modules.publication.coverage import profile_for

    profile = profile_for(territory)
    if profile is None:
        raise TerritoryNotConfigured(territory)
    return profile
