import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("evidence", "0010_property_presentations")]

    operations = [
        migrations.RunSQL(
            """DO $$ BEGIN
                PERFORM pg_advisory_xact_lock(716548219);
                PERFORM pg_advisory_xact_lock(716548220);
                IF EXISTS (
                    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname IN ('ingestion_execution', 'ingestion_execution_run')
                    AND n.nspname IN ('public', 'real_estate', 'evidence')
                ) THEN
                    RAISE EXCEPTION 'Ingestion execution tables would collide';
                END IF;
            END $$;""",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.CreateModel(
            name="IngestionExecution",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("execution_key", models.CharField(max_length=64, unique=True)),
                ("operation", models.CharField(max_length=40)),
                ("scope", models.CharField(max_length=100)),
                ("actor", models.CharField(max_length=160)),
                ("input_sha256", models.CharField(max_length=64, null=True)),
                ("prefect_flow_run_id", models.UUIDField(null=True)),
                ("attempts", models.PositiveIntegerField(default=1)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(null=True)),
                ("status", models.CharField(default="running", max_length=20)),
                ("error", models.CharField(blank=True, max_length=160)),
                ("summary", models.JSONField(default=dict)),
                (
                    "runs",
                    models.ManyToManyField(
                        db_table="ingestion_execution_run",
                        related_name="executions",
                        to="evidence.ingestionrun",
                    ),
                ),
            ],
            options={
                "db_table": "ingestion_execution",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("operation", "scope", "input_sha256"),
                        condition=models.Q(
                            input_sha256__isnull=False, status__in=["succeeded", "quarantined"]
                        ),
                        name="ingestion_execution_receipt_identity",
                    ),
                    models.CheckConstraint(
                        condition=(
                            models.Q(status="running", finished_at__isnull=True)
                            | models.Q(
                                status__in=["succeeded", "quarantined", "failed"],
                                finished_at__isnull=False,
                                finished_at__gte=models.F("started_at"),
                            )
                        ),
                        name="ingestion_execution_lifecycle_valid",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            execution_key__regex=r"^[0-9a-f]{64}$",
                            actor__regex=r"\S",
                            attempts__gte=1,
                            operation__in=[
                                "onwani",
                                "map",
                                "references",
                                "property_presentations",
                                "imagery",
                            ],
                        ),
                        name="ingestion_execution_identity_valid",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(input_sha256__isnull=True)
                        | models.Q(input_sha256__regex=r"^[0-9a-f]{64}$"),
                        name="ingestion_execution_receipt_hash_valid",
                    ),
                ],
            },
        ),
        migrations.RunSQL(
            "ALTER TABLE public.ingestion_execution SET SCHEMA evidence; "
            "ALTER TABLE public.ingestion_execution_run SET SCHEMA evidence;",
            reverse_sql="ALTER TABLE evidence.ingestion_execution_run SET SCHEMA public; "
            "ALTER TABLE evidence.ingestion_execution SET SCHEMA public;",
        ),
    ]
