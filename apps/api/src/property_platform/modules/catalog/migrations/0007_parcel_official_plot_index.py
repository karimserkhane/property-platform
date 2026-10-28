from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0006_developer_project"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="parcel",
            index=models.Index(
                fields=["official_plot_id", "municipality", "district"],
                name="parcel_official_plot",
            ),
        ),
    ]
