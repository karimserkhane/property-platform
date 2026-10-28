"""Allow raw capture bodies in private object storage (task A10).

Only the metadata check is widened: existing rows, keys and journals are unchanged.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("evidence", "0036_row_revision_cache_indexes")]

    operations = [
        migrations.RemoveConstraint(
            model_name="storedobject",
            name="stored_object_metadata_valid",
        ),
        migrations.AddConstraint(
            model_name="storedobject",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    backend__in=["local", "s3"],
                    namespace__regex=r"^[a-z0-9][a-z0-9-]{0,62}$",
                    content_sha256__regex=r"^[0-9a-f]{64}$",
                    byte_length__gte=1,
                    byte_length__lte=134217728,
                    mime_type__in=[
                        "image/jpeg",
                        "image/png",
                        "image/webp",
                        "application/pdf",
                        "video/mp4",
                        "video/webm",
                        "model/gltf-binary",
                        "application/octet-stream",
                    ],
                ),
                name="stored_object_metadata_valid",
            ),
        ),
    ]
