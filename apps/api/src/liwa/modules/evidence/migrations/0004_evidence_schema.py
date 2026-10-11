from django.db import migrations

# Literal, migration-local mapping: don't import runtime model definitions here.
TABLES = (
    ("source", "evidence_source", "source"),
    ("ingestionrun", "evidence_ingestionrun", "ingestion_run"),
    ("capture", "evidence_capture", "capture"),
    ("parcelobservation", "evidence_parcelobservation", "parcel_observation"),
    ("auditevent", "evidence_auditevent", "audit_event"),
    ("quarantinedobservation", "evidence_quarantinedobservation", "quarantined_observation"),
)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_real_estate_schema"),
        ("evidence", "0003_enforce_data_integrity"),
    ]

    operations = [
        migrations.RunSQL(
            "SELECT pg_advisory_xact_lock(716548219); CREATE SCHEMA IF NOT EXISTS evidence;",
            reverse_sql="SELECT pg_advisory_xact_lock(716548219);",
        ),
        *[
            migrations.SeparateDatabaseAndState(
                database_operations=[
                    migrations.RunSQL(
                        sql=f"""
                            DO $$ BEGIN
                                IF to_regclass('public.{new}') IS NOT NULL
                                   OR to_regclass('real_estate.{new}') IS NOT NULL THEN
                                    RAISE EXCEPTION 'Domain table {new} would be shadowed';
                                END IF;
                            END $$;
                            ALTER TABLE public.{old} SET SCHEMA evidence;
                            ALTER TABLE evidence.{old} RENAME TO {new};
                        """,
                        reverse_sql=f"""
                            ALTER TABLE evidence.{new} RENAME TO {old};
                            ALTER TABLE evidence.{old} SET SCHEMA public;
                        """,
                    ),
                ],
                state_operations=[migrations.AlterModelTable(name=model, table=new)],
            )
            for model, old, new in TABLES
        ],
    ]
