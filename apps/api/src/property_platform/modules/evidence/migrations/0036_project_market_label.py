import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0006_developer_project"),
        ("evidence", "0035_construction_activity_measurement"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectMarketLabel",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("district", models.CharField(max_length=255)),
                ("label", models.CharField(max_length=255)),
                ("evidence", models.CharField(max_length=20)),
                ("registration_number", models.CharField(blank=True, max_length=40)),
                ("basis", models.CharField(max_length=500)),
                ("reviewed_on", models.DateField()),
                ("actor", models.CharField(max_length=160)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("revoked_at", models.DateTimeField(null=True)),
                ("revoked_by", models.CharField(blank=True, max_length=160)),
                ("revocation_reason", models.CharField(blank=True, max_length=500)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="market_labels",
                        to="catalog.project",
                    ),
                ),
            ],
            options={
                "db_table": "project_market_label",
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            ("actor__regex", "\\S"),
                            ("basis__regex", "\\S"),
                            ("district__regex", "\\S"),
                            ("label__regex", "\\S"),
                            models.Q(
                                models.Q(("evidence", "project_name"), ("registration_number", "")),
                                models.Q(
                                    ("evidence", "register_name"),
                                    ("registration_number__regex", "^[0-9][0-9/]{5,39}$"),
                                ),
                                _connector="OR",
                            ),
                        ),
                        name="project_market_label_review_present",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("active", True)),
                        fields=("district", "label"),
                        name="project_market_label_one_active",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                ("active", True),
                                ("revocation_reason", ""),
                                ("revoked_at__isnull", True),
                                ("revoked_by", ""),
                            ),
                            models.Q(
                                ("active", False),
                                ("revocation_reason__regex", "\\S"),
                                ("revoked_at__gte", models.F("created_at")),
                                ("revoked_at__isnull", False),
                                ("revoked_by__regex", "\\S"),
                            ),
                            _connector="OR",
                        ),
                        name="project_market_label_revocation_valid",
                    ),
                ],
            },
        ),
        # Evidence tables live in the evidence schema and are journalled like the others.
        migrations.RunSQL(
            "ALTER TABLE public.project_market_label SET SCHEMA evidence; "
            "SELECT evidence.install_row_journals(false);",
            reverse_sql="DROP TRIGGER journal_row ON evidence.project_market_label; "
            "ALTER TABLE evidence.project_market_label SET SCHEMA public;",
        ),
    ]
