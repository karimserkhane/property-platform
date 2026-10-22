"""Database-clock audit of owned business tables, including a labelled initial inventory."""

from django.db import migrations

INSTALL = r"""
CREATE FUNCTION evidence.journal_row() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, evidence AS $$
DECLARE previous jsonb; current_row jsonb; identity_row jsonb;
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        EXECUTE format('SELECT to_jsonb(r) FROM (SELECT %s) r', TG_ARGV[0]) INTO previous USING OLD;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        EXECUTE format('SELECT to_jsonb(r) FROM (SELECT %s) r', TG_ARGV[0])
            INTO current_row USING NEW;
    END IF;
    IF TG_OP = 'UPDATE' AND previous IS NOT DISTINCT FROM current_row THEN RETURN NEW; END IF;
    identity_row := coalesce(current_row, previous);
    INSERT INTO evidence.row_revision
        (schema_name, table_name, row_key, operation, recorded_at, known_ingested_at,
         transaction_id, actor, execution_key, before, after)
    VALUES (TG_TABLE_SCHEMA, TG_TABLE_NAME, identity_row->>TG_ARGV[1], TG_OP, clock_timestamp(),
        coalesce(identity_row->>'ingested_at', identity_row->>'created_at')::timestamptz,
        pg_current_xact_id()::text,
        coalesce(nullif(current_setting('platform.actor', true), ''),
            nullif(identity_row->>'actor', ''), session_user),
        coalesce(current_setting('platform.execution_key', true), ''), previous, current_row);
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION evidence.protect_journal() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'The row journal is append-only'; END $$;
CREATE TRIGGER protect_journal BEFORE UPDATE OR DELETE ON evidence.row_revision
    FOR EACH ROW EXECUTE FUNCTION evidence.protect_journal();

CREATE FUNCTION evidence.install_row_journals(baseline boolean DEFAULT false) RETURNS void
LANGUAGE plpgsql SET search_path = pg_catalog, evidence AS $$
DECLARE target record; columns_sql text; baseline_columns text; primary_key text;
BEGIN
    FOR target IN SELECT c.oid, n.nspname, c.relname FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname IN ('real_estate', 'evidence') AND c.relkind='r'
        AND c.relname <> 'row_revision' ORDER BY n.nspname, c.relname
    LOOP
        -- Never copy binary payloads to JSON. Capture/object checksums and their
        -- immutable byte storage already provide their evidence identity.
        SELECT string_agg(CASE WHEN a.atttypid='bytea'::regtype THEN
                 format('encode(sha256(($1).%I), ''hex'') AS %I',
                    a.attname, a.attname || '_sha256')
                 ELSE format('($1).%I', a.attname) END, ', ' ORDER BY a.attnum),
               string_agg(CASE WHEN a.atttypid='bytea'::regtype THEN
                 format('encode(sha256(t.%I), ''hex'') AS %I',
                    a.attname, a.attname || '_sha256')
                 ELSE format('t.%I', a.attname) END, ', ' ORDER BY a.attnum)
        INTO columns_sql, baseline_columns FROM pg_attribute a
        WHERE a.attrelid=target.oid AND a.attnum>0 AND NOT a.attisdropped;
        SELECT a.attname INTO STRICT primary_key FROM pg_index i
            JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=ANY(i.indkey)
            WHERE i.indrelid=target.oid AND i.indisprimary;
        EXECUTE format('CREATE OR REPLACE TRIGGER journal_row '
            'AFTER INSERT OR UPDATE OR DELETE ON %I.%I '
            'FOR EACH ROW EXECUTE FUNCTION evidence.journal_row(%L, %L)',
            target.nspname, target.relname, columns_sql, primary_key);
        IF baseline THEN
            EXECUTE format($sql$
                INSERT INTO evidence.row_revision
                  (schema_name, table_name, row_key, operation, recorded_at, known_ingested_at,
                   transaction_id, actor, execution_key, before, after)
                SELECT %L, %L, r.data->>%L, 'BASELINE', clock_timestamp(),
                       coalesce(r.data->>'ingested_at', r.data->>'created_at')::timestamptz,
                       pg_current_xact_id()::text, 'migration:0023', '', NULL, r.data
                FROM (SELECT to_jsonb(s) AS data FROM %I.%I t
                      CROSS JOIN LATERAL (SELECT %s) s) r
            $sql$, target.nspname, target.relname, primary_key,
                target.nspname, target.relname, baseline_columns);
        END IF;
    END LOOP;
END $$;

CREATE FUNCTION evidence.protect_capture_bytes() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,evidence AS $$
BEGIN
    IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'Original evidence cannot be deleted' USING ERRCODE='23514';
    END IF;
    IF NEW.content_sha256 <> OLD.content_sha256 OR NEW.byte_length <> OLD.byte_length THEN
        RAISE EXCEPTION 'Original evidence fingerprint is immutable' USING ERRCODE='23514';
    END IF;
    IF NEW.payload IS DISTINCT FROM OLD.payload THEN
        IF NEW.payload IS NOT NULL THEN
            IF OLD.payload IS NOT NULL
               OR encode(sha256(NEW.payload),'hex') <> OLD.content_sha256 THEN
                RAISE EXCEPTION 'Original evidence bytes are immutable' USING ERRCODE='23514';
            END IF;
        ELSIF NOT EXISTS(SELECT 1 FROM evidence.stored_object o
            WHERE o.id=NEW.primary_object_id AND o.content_sha256=OLD.content_sha256
                AND o.byte_length=OLD.byte_length AND o.verified_at IS NOT NULL) THEN
            RAISE EXCEPTION 'Evidence relocation requires a verified copy' USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER protect_capture_bytes BEFORE UPDATE OR DELETE ON evidence.capture
    FOR EACH ROW EXECUTE FUNCTION evidence.protect_capture_bytes();
SELECT evidence.install_row_journals(true);
"""

UNINSTALL = """
DO $$ DECLARE target record; BEGIN
    FOR target IN SELECT event_object_schema AS s, event_object_table AS t
        FROM information_schema.triggers WHERE trigger_name='journal_row'
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS journal_row ON %I.%I', target.s, target.t);
    END LOOP;
END $$;
DROP FUNCTION evidence.install_row_journals(boolean);
DROP FUNCTION evidence.journal_row();
DROP TRIGGER protect_journal ON evidence.row_revision;
DROP FUNCTION evidence.protect_journal();
DROP TRIGGER protect_capture_bytes ON evidence.capture;
DROP FUNCTION evidence.protect_capture_bytes();
"""


class Migration(migrations.Migration):
    dependencies = [("evidence", "0022_row_history")]
    operations = [migrations.RunSQL(INSTALL, reverse_sql=UNINSTALL)]
