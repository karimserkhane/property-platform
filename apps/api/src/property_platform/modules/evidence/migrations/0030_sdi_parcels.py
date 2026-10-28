from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("evidence", "0029_project_registration_claims")]
    operations = [
        migrations.RemoveConstraint(
            model_name="ingestionexecution", name="ingestion_execution_identity_valid"
        ),
        migrations.AddConstraint(
            model_name="ingestionexecution",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    execution_key__regex=r"^[0-9a-f]{64}$",
                    actor__regex=r"\S",
                    attempts__gte=1,
                    operation__in=[
                        "sdi_parcels",
                        "onwani",
                        "map",
                        "references",
                        "property_presentations",
                        "imagery",
                        "osm_bootstrap",
                        "adrec_sales",
                        "adrec_indices",
                        "public_context",
                        "project_details",
                        "project_discovery",
                    ],
                ),
                name="ingestion_execution_identity_valid",
            ),
        ),
    ]
