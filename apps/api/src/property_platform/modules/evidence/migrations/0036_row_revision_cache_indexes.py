"""Indexes for read-cache versions per table family (task A08)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("evidence", "0035_construction_activity_measurement")]

    operations = [
        migrations.AddIndex(
            model_name="rowrevision",
            index=models.Index(
                fields=["schema_name", "table_name", "id"], name="row_revision_table_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="rowrevision",
            index=models.Index(
                fields=["transaction_id", "schema_name", "table_name"],
                name="row_revision_transaction_idx",
            ),
        ),
    ]
