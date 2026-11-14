"""A45: throwaway databases from template_postgis skip only what the template provides."""

from types import SimpleNamespace

from property_platform_ingestion import scratch_template

# Shape of `pg_restore --list` for a full dump of the PostGIS image's database.
TOC = """;
; Archive created at 2026-11-14 03:00:00 UTC
;
12; 2615 19830 SCHEMA - real_estate property_platform
11; 2615 19385 SCHEMA - tiger property_platform
10; 2615 19184 SCHEMA - topology property_platform
4801; 0 0 COMMENT - SCHEMA topology property_platform
2; 3079 18102 EXTENSION - postgis
4803; 0 0 COMMENT - EXTENSION postgis
6; 3079 19900 EXTENSION - pg_trgm
4806; 0 0 COMMENT - EXTENSION pg_trgm
288; 1259 19831 TABLE real_estate parcel property_platform
4525; 0 18421 TABLE DATA public spatial_ref_sys property_platform
4793; 0 19831 TABLE DATA real_estate parcel property_platform
4529; 0 19392 TABLE DATA tiger geocode_settings property_platform
4806; 0 0 SEQUENCE SET topology topology_id_seq property_platform
4807; 0 0 SEQUENCE SET real_estate parcel_id_seq property_platform
4900; 0 0 COMMENT real_estate TABLE parcel property_platform
4640; 2606 19838 CONSTRAINT real_estate parcel parcel_pkey property_platform
"""

PROVIDED = {
    "extensions": {"plpgsql", "postgis", "postgis_topology"},
    "schemas": {"public", "pg_catalog", "information_schema", "tiger", "topology"},
    "members": {
        ("public", "spatial_ref_sys"),
        ("tiger", "geocode_settings"),
        ("topology", "topology_id_seq"),
    },
}


def test_restore_list_keeps_business_objects_and_skips_template_objects():
    listing, skipped = scratch_template.restore_list(TOC, PROVIDED)
    kept = [line for line in listing.splitlines() if not line.startswith(";")]
    assert kept == [
        "12; 2615 19830 SCHEMA - real_estate property_platform",
        "6; 3079 19900 EXTENSION - pg_trgm",
        "4806; 0 0 COMMENT - EXTENSION pg_trgm",
        "288; 1259 19831 TABLE real_estate parcel property_platform",
        "4793; 0 19831 TABLE DATA real_estate parcel property_platform",
        "4807; 0 0 SEQUENCE SET real_estate parcel_id_seq property_platform",
        "4900; 0 0 COMMENT real_estate TABLE parcel property_platform",
        "4640; 2606 19838 CONSTRAINT real_estate parcel parcel_pkey property_platform",
    ]
    assert skipped == 8
    # Comment lines of the archive header stay, so pg_restore still reads the list.
    assert listing.startswith(";\n")


def test_nothing_is_skipped_when_the_template_provides_nothing():
    empty = {"extensions": set(), "schemas": set(), "members": set()}
    listing, skipped = scratch_template.restore_list(TOC, empty)
    assert skipped == 0
    assert listing == TOC


def admin(exists):
    return SimpleNamespace(
        execute=lambda query, params: SimpleNamespace(fetchone=lambda: (exists,))
    )


def test_template_clause_prefers_template_postgis_and_falls_back():
    assert (
        scratch_template.template_clause(admin(True), "template0").as_string()
        == ' TEMPLATE "template_postgis"'
    )
    assert (
        scratch_template.template_clause(admin(False), "template0").as_string()
        == ' TEMPLATE "template0"'
    )
    assert scratch_template.template_clause(admin(False)).as_string() == ""
