# Every collected or derived row with the reviewed rights of the site it was read from (A23).

from django.db import migrations, models

FUNCTIONS = r"""
CREATE FUNCTION evidence.url_host(url text) RETURNS text
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT lower(substring(url from '^[A-Za-z][A-Za-z0-9+.-]*://(?:[^/?#@]*@)?([^/?#:]+)')) $$;

-- The active review of a host or of the domain it belongs to; listed hosts never nest.
CREATE FUNCTION evidence.reviewed_rights_id(host text) RETURNS bigint
LANGUAGE sql STABLE STRICT PARALLEL SAFE
AS $$
    SELECT r.id FROM evidence.source_rights r
    WHERE r.active AND ($1 = r.host OR right($1, length(r.host) + 1) = '.' || r.host)
    ORDER BY length(r.host) DESC LIMIT 1
$$;

-- Not mirrored yet means not enforced, as decided on 27 October 2026 (A22).
CREATE FUNCTION evidence.right_enforced(name text) RETURNS boolean
LANGUAGE sql STABLE STRICT PARALLEL SAFE
AS $$
    SELECT coalesce(
        (SELECT e.enforced FROM evidence.source_rights_enforcement e
         WHERE e.active AND e.name = $1),
        false)
$$;
"""

# One row per data row and per capture it was read from. A capture inherits the rights
# of its host; a local computation (an internal or documentation URL that no review
# lists) inherits those of the nearest parent capture whose host is listed. Rows known
# only by a link (a developer site, a register page, a search entry) take the rights of
# the host of that link. Nothing is copied: a revised review changes every row at once.
DATA_RIGHTS = r"""
CREATE VIEW evidence.data_rights AS
WITH RECURSIVE lineage(capture_id, rights_capture_id, parent_capture_id, url, rights_id, depth) AS (
    SELECT c.id, c.id, c.parent_capture_id, c.url::text,
           evidence.reviewed_rights_id(evidence.url_host(c.url)), 0
    FROM evidence.capture c
    UNION ALL
    SELECT l.capture_id, p.id, p.parent_capture_id, p.url::text,
           evidence.reviewed_rights_id(evidence.url_host(p.url)), l.depth + 1
    FROM lineage l JOIN evidence.capture p ON p.id = l.parent_capture_id
    WHERE l.rights_id IS NULL AND l.depth < 16
),
capture_rights AS (
    SELECT DISTINCT ON (capture_id) capture_id, rights_capture_id, url, rights_id
    FROM lineage
    ORDER BY capture_id, rights_id IS NULL, depth
),
data_rows(dataset, row_id, capture_id, url) AS (
    SELECT 'evidence.capture'::text, c.id::text, c.id, NULL::text FROM evidence.capture c
    UNION ALL SELECT 'evidence.parcel_observation', o.id::text, o.capture_id, NULL
        FROM evidence.parcel_observation o
    UNION ALL SELECT 'evidence.map_observation', o.id::text, o.capture_id, NULL
        FROM evidence.map_observation o
    UNION ALL SELECT 'evidence.quarantined_observation', o.id::text, o.capture_id, NULL
        FROM evidence.quarantined_observation o
    UNION ALL SELECT 'evidence.parcel_source_alias', a.id::text, a.capture_id, NULL
        FROM evidence.parcel_source_alias a
    UNION ALL SELECT 'evidence.administrative_area_source_alias', a.id::text, a.capture_id, NULL
        FROM evidence.administrative_area_source_alias a
    UNION ALL SELECT 'evidence.adrec_market_snapshot', s.id::text, o.capture_id, NULL
        FROM evidence.adrec_market_snapshot s
        LEFT JOIN (
            SELECT snapshot_id, capture_id FROM evidence.adrec_sale_observation
            UNION SELECT snapshot_id, capture_id FROM evidence.adrec_index_observation
        ) o ON o.snapshot_id = s.id
    UNION ALL SELECT 'evidence.adrec_sale_observation', o.id::text, o.capture_id, NULL
        FROM evidence.adrec_sale_observation o
    UNION ALL SELECT 'evidence.adrec_index_observation', o.id::text, o.capture_id, NULL
        FROM evidence.adrec_index_observation o
    UNION ALL SELECT 'evidence.public_context_snapshot', s.id::text, s.capture_id, NULL
        FROM evidence.public_context_snapshot s
    UNION ALL SELECT 'evidence.health_facility_observation', o.id::text, s.capture_id, NULL
        FROM evidence.health_facility_observation o
        JOIN evidence.public_context_snapshot s ON s.id = o.snapshot_id
    UNION ALL SELECT 'evidence.school_observation', o.id::text, s.capture_id, NULL
        FROM evidence.school_observation o
        JOIN evidence.public_context_snapshot s ON s.id = o.snapshot_id
    UNION ALL SELECT 'evidence.bus_route_observation', o.id::text, s.capture_id, NULL
        FROM evidence.bus_route_observation o
        JOIN evidence.public_context_snapshot s ON s.id = o.snapshot_id
    UNION ALL SELECT 'evidence.district_boundary_observation', o.id::text, s.capture_id, NULL
        FROM evidence.district_boundary_observation o
        JOIN evidence.public_context_snapshot s ON s.id = o.snapshot_id
    UNION ALL SELECT 'evidence.census_measure_observation', o.id::text, s.capture_id, NULL
        FROM evidence.census_measure_observation o
        JOIN evidence.public_context_snapshot s ON s.id = o.snapshot_id
    UNION ALL SELECT 'evidence.project_snapshot', s.id::text, s.capture_id, NULL
        FROM evidence.project_snapshot s
    UNION ALL SELECT 'evidence.project_typology', t.id::text, s.capture_id, NULL
        FROM evidence.project_typology t JOIN evidence.project_snapshot s ON s.id = t.snapshot_id
    UNION ALL SELECT 'evidence.project_amenity', a.id::text, s.capture_id, NULL
        FROM evidence.project_amenity a JOIN evidence.project_snapshot s ON s.id = a.snapshot_id
    UNION ALL SELECT 'evidence.project_verification', v.id::text, s.capture_id, NULL
        FROM evidence.project_verification v
        JOIN evidence.project_snapshot s ON s.id = v.snapshot_id
    UNION ALL SELECT 'evidence.project_media', m.id::text, s.capture_id, NULL
        FROM evidence.project_media m JOIN evidence.project_snapshot s ON s.id = m.snapshot_id
    UNION ALL SELECT 'evidence.project_media_publication', p.media_id::text, s.capture_id, NULL
        FROM evidence.project_media_publication p
        JOIN evidence.project_media m ON m.id = p.media_id
        JOIN evidence.project_snapshot s ON s.id = m.snapshot_id
    UNION ALL SELECT 'evidence.project_identity_link', l.id::text, l.capture_id, NULL
        FROM evidence.project_identity_link l
    UNION ALL SELECT 'evidence.project_relation', r.id::text, r.capture_id, NULL
        FROM evidence.project_relation r
    UNION ALL SELECT 'evidence.project_source_candidate', c.id::text, c.capture_id, NULL
        FROM evidence.project_source_candidate c
    UNION ALL SELECT 'evidence.project_verification_link', l.id::text, NULL, l.url::text
        FROM evidence.project_verification_link l
    UNION ALL SELECT 'evidence.property_presentation', p.id::text, p.capture_id, NULL
        FROM evidence.property_presentation p
    UNION ALL SELECT 'evidence.property_media', m.id::text, m.capture_id, NULL
        FROM evidence.property_media m
    UNION ALL SELECT 'evidence.media_publication', p.media_id::text, m.capture_id, NULL
        FROM evidence.media_publication p JOIN evidence.property_media m ON m.id = p.media_id
    UNION ALL SELECT 'evidence.research_reference', r.id::text, r.capture_id, NULL
        FROM evidence.research_reference r
    UNION ALL SELECT 'evidence.basemap_tile', t.id::text, t.capture_id, NULL
        FROM evidence.basemap_tile t
    UNION ALL SELECT 'evidence.imagery_scene', s.id::text, s.capture_id, NULL
        FROM evidence.imagery_scene s
    UNION ALL SELECT 'evidence.construction_activity_measurement', m.id::text, w.capture_id, NULL
        FROM evidence.construction_activity_measurement m
        CROSS JOIN LATERAL (VALUES (m.before_capture_id), (m.after_capture_id)) w(capture_id)
    UNION ALL SELECT 'evidence.routing_graph', g.id::text, g.capture_id, NULL
        FROM evidence.routing_graph g
    UNION ALL SELECT 'evidence.routing_graph_part', p.id::text, p.capture_id, NULL
        FROM evidence.routing_graph_part p
    UNION ALL SELECT 'evidence.walking_area', w.id::text, w.capture_id, NULL
        FROM evidence.walking_area w
    UNION ALL SELECT 'evidence.evidence_search_entry', e.id::text, NULL, e.source_url::text
        FROM evidence.evidence_search_entry e
    UNION ALL SELECT 'evidence.evidence_search_embedding', v.id::text, NULL, e.source_url::text
        FROM evidence.evidence_search_embedding v
        JOIN evidence.evidence_search_entry e ON e.id = v.entry_id
    UNION ALL SELECT 'real_estate.parcel', p.id::text, o.capture_id, NULL
        FROM real_estate.parcel p
        LEFT JOIN (SELECT DISTINCT parcel_id, capture_id FROM evidence.parcel_observation) o
            ON o.parcel_id = p.id
    UNION ALL SELECT 'real_estate.building', b.id::text, o.capture_id, NULL
        FROM real_estate.building b
        LEFT JOIN (
            SELECT building_id, capture_id FROM evidence.map_observation
            WHERE building_id IS NOT NULL
            UNION SELECT building_id, capture_id FROM evidence.project_identity_link
            WHERE building_id IS NOT NULL
            UNION SELECT building_id, capture_id FROM evidence.property_presentation
            WHERE building_id IS NOT NULL
        ) o ON o.building_id = b.id
    UNION ALL SELECT 'real_estate.place', p.id::text, o.capture_id, NULL
        FROM real_estate.place p
        LEFT JOIN (
            SELECT place_id, capture_id FROM evidence.map_observation WHERE place_id IS NOT NULL
            UNION SELECT place_id, capture_id FROM evidence.project_identity_link
            WHERE place_id IS NOT NULL
            UNION SELECT place_id, capture_id FROM evidence.property_presentation
            WHERE place_id IS NOT NULL
            UNION SELECT place_id, capture_id FROM evidence.research_reference
            WHERE place_id IS NOT NULL
        ) o ON o.place_id = p.id
    UNION ALL SELECT 'real_estate.street', s.id::text, o.capture_id, NULL
        FROM real_estate.street s
        LEFT JOIN (
            SELECT DISTINCT street_id, capture_id FROM evidence.map_observation
            WHERE street_id IS NOT NULL
        ) o ON o.street_id = s.id
    UNION ALL SELECT 'real_estate.administrative_area', a.id::text, o.capture_id, NULL
        FROM real_estate.administrative_area a
        LEFT JOIN (
            SELECT administrative_area_id AS area_id, capture_id FROM evidence.map_observation
            WHERE administrative_area_id IS NOT NULL
            UNION SELECT administrative_area_id, capture_id
            FROM evidence.administrative_area_source_alias
        ) o ON o.area_id = a.id
    UNION ALL SELECT 'real_estate.project', p.id::text, s.capture_id,
            CASE WHEN s.capture_id IS NULL THEN p.website_url::text END
        FROM real_estate.project p
        LEFT JOIN (SELECT DISTINCT project_id, capture_id FROM evidence.project_snapshot) s
            ON s.project_id = p.id
    UNION ALL SELECT 'real_estate.developer', d.id::text, NULL, d.website_url::text
        FROM real_estate.developer d
),
resolved AS (
    SELECT d.dataset, d.row_id, d.capture_id,
           coalesce(r.url, d.url) AS source_url,
           coalesce(r.rights_capture_id <> r.capture_id, false) AS inherited,
           CASE WHEN d.capture_id IS NULL
                THEN evidence.reviewed_rights_id(evidence.url_host(d.url))
                ELSE r.rights_id END AS rights_id
    FROM data_rows d LEFT JOIN capture_rights r ON r.capture_id = d.capture_id
),
switch AS (SELECT evidence.right_enforced('publication') AS publication_enforced)
SELECT x.dataset,
       x.row_id,
       x.capture_id,
       x.source_url,
       evidence.url_host(x.source_url) AS source_host,
       x.inherited AS rights_from_parent_capture,
       s.id AS source_rights_id,
       s.host AS reviewed_host,
       coalesce(s.publisher, '') AS publisher,
       coalesce(s.licence, 'unknown') AS licence,
       nullif(s.licence_url, '') AS licence_url,
       nullif(s.terms_url, '') AS terms_url,
       s.reviewed_on,
       coalesce(s.reviewed_by, '') AS reviewed_by,
       coalesce(s.collection, 'allowed') AS collection,
       coalesce(s.publication, 'facts') AS publication,
       nullif(s.attribution, '') AS attribution,
       s.reviewed_on IS NOT NULL AS qualified,
       x.capture_id IS NOT NULL AND coalesce(s.collection, 'allowed') = 'forbidden'
           AS collected_against_terms,
       coalesce(s.publication, 'facts') IN ('link', 'none') AND NOT w.publication_enforced
           AS shown_beyond_terms
FROM resolved x
CROSS JOIN switch w
LEFT JOIN evidence.source_rights s ON s.id = x.rights_id;

CREATE VIEW evidence.data_rights_summary AS
SELECT dataset, licence, collection, publication, qualified, collected_against_terms,
       shown_beyond_terms, count(*) AS rows, count(DISTINCT source_host) AS hosts
FROM evidence.data_rights
GROUP BY dataset, licence, collection, publication, qualified, collected_against_terms,
         shown_beyond_terms;
"""

DROP = """
DROP VIEW evidence.data_rights_summary;
DROP VIEW evidence.data_rights;
DROP FUNCTION evidence.right_enforced(text);
DROP FUNCTION evidence.reviewed_rights_id(text);
DROP FUNCTION evidence.url_host(text);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("evidence", "0041_evidence_search_embedding"),
    ]

    operations = [
        migrations.CreateModel(
            name="SourceRightsEnforcement",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=20)),
                ("enforced", models.BooleanField()),
                ("decided_on", models.DateField()),
                ("decided_by", models.CharField(max_length=80)),
                ("basis", models.CharField(max_length=500)),
                ("actor", models.CharField(max_length=160)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("revoked_at", models.DateTimeField(null=True)),
                ("revoked_by", models.CharField(blank=True, max_length=160)),
                ("revocation_reason", models.CharField(blank=True, max_length=500)),
            ],
            options={
                "db_table": "source_rights_enforcement",
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            ("actor__regex", "\\S"),
                            ("basis__regex", "\\S"),
                            ("decided_by__regex", "\\S"),
                            ("name__in", ("collection", "publication")),
                        ),
                        name="source_rights_enforcement_decided",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("active", True)),
                        fields=("name",),
                        name="source_rights_enforcement_one_active",
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
                        name="source_rights_enforcement_revocation_valid",
                    ),
                ],
            },
        ),
        # Evidence tables live in the evidence schema and are journalled like the others.
        migrations.RunSQL(
            "ALTER TABLE public.source_rights_enforcement SET SCHEMA evidence; "
            "SELECT evidence.install_row_journals(false);",
            reverse_sql="DROP TRIGGER journal_row ON evidence.source_rights_enforcement; "
            "ALTER TABLE evidence.source_rights_enforcement SET SCHEMA public;",
        ),
        migrations.RunSQL(FUNCTIONS + DATA_RIGHTS, reverse_sql=DROP),
    ]
