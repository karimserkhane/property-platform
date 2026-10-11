from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_enforce_data_integrity"),
        ("evidence", "0003_enforce_data_integrity"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        SELECT pg_advisory_xact_lock(716548219);
                        CREATE SCHEMA IF NOT EXISTS real_estate;
                        DO $$ BEGIN
                            IF to_regclass('public.parcel') IS NOT NULL THEN
                                RAISE EXCEPTION 'public.parcel would shadow the domain table';
                            END IF;
                        END $$;
                        ALTER TABLE public.catalog_parcel SET SCHEMA real_estate;
                        ALTER TABLE real_estate.catalog_parcel RENAME TO parcel;
                    """,
                    reverse_sql="""
                        SELECT pg_advisory_xact_lock(716548219);
                        ALTER TABLE real_estate.parcel RENAME TO catalog_parcel;
                        ALTER TABLE real_estate.catalog_parcel SET SCHEMA public;
                    """,
                ),
            ],
            state_operations=[migrations.AlterModelTable(name="parcel", table="parcel")],
        ),
    ]
