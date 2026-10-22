from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("evidence", "0027_project_source_provenance")]

    operations = [
        migrations.AlterField(
            model_name="ingestionexecution",
            name="scope",
            field=models.CharField(max_length=255),
        )
    ]
