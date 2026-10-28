import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("evidence", "0040_evidence_search_entry"),
    ]

    operations = [
        migrations.CreateModel(
            name="EvidenceSearchEmbedding",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("model", models.CharField(max_length=200)),
                ("vector", models.BinaryField()),
                ("ingested_at", models.DateTimeField(auto_now_add=True)),
                (
                    "entry",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="embedding",
                        to="evidence.evidencesearchentry",
                    ),
                ),
                (
                    "run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="evidence.ingestionrun"
                    ),
                ),
            ],
            options={
                "db_table": "evidence_search_embedding",
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("model__regex", r"^[^@\s]+@[a-f0-9]{40}$")),
                        name="evidence_search_embedding_valid",
                    )
                ],
            },
        ),
        # Evidence tables live in the evidence schema and are journalled like the others.
        migrations.RunSQL(
            "ALTER TABLE public.evidence_search_embedding SET SCHEMA evidence; "
            "SELECT evidence.install_row_journals(false);",
            reverse_sql="DROP TRIGGER journal_row ON evidence.evidence_search_embedding; "
            "ALTER TABLE evidence.evidence_search_embedding SET SCHEMA public;",
        ),
    ]
