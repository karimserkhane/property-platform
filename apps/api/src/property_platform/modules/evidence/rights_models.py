"""Reviewed source rights mirrored from `source_rights.json`, with their history (A19)."""

from django.db import models

from .source_rights import COLLECTION, PUBLICATION


class SourceRights(models.Model):
    """One active review per host; a revised or removed review is revoked, never deleted.

    Rows hold what a reviewer decided for a site, not a copy per capture: a capture,
    observation or fact inherits the rights of the host of the URL it was read from.
    """

    host = models.CharField(max_length=255)
    publisher = models.CharField(max_length=160)
    licence = models.CharField(max_length=80)
    licence_url = models.URLField(max_length=1000, blank=True)
    terms_url = models.URLField(max_length=1000, blank=True)
    reviewed_on = models.DateField(null=True)
    reviewed_by = models.CharField(max_length=160, blank=True)
    collection = models.CharField(max_length=20)
    publication = models.CharField(max_length=20)
    attribution = models.CharField(max_length=300, blank=True)
    basis = models.CharField(max_length=500)
    actor = models.CharField(max_length=160)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True)
    revoked_by = models.CharField(max_length=160, blank=True)
    revocation_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "source_rights"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    host__regex=r"^[a-z0-9-]+(\.[a-z0-9-]+)+$",
                    collection__in=COLLECTION,
                    publication__in=PUBLICATION,
                    publisher__regex=r"\S",
                    licence__regex=r"\S",
                    basis__regex=r"\S",
                    actor__regex=r"\S",
                ),
                name="source_rights_review_present",
            ),
            models.UniqueConstraint(
                fields=["host"],
                condition=models.Q(active=True),
                name="source_rights_one_active",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    active=True, revoked_at__isnull=True, revoked_by="", revocation_reason=""
                )
                | models.Q(
                    active=False,
                    revoked_at__isnull=False,
                    revoked_at__gte=models.F("created_at"),
                    revoked_by__regex=r"\S",
                    revocation_reason__regex=r"\S",
                ),
                name="source_rights_revocation_valid",
            ),
        ]
