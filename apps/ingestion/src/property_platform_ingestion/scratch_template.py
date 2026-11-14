"""Throwaway databases that a role without superuser rights can create and fill (A45).

PostGIS is not a trusted extension: only a superuser may CREATE EXTENSION postgis. The
official PostGIS image ships `template_postgis`, a template with PostGIS (and topology,
tiger geocoder) already installed, so a CREATEDB role can create a spatial database from
it. Restoring a full dump there must then skip what the template already provides:
the extensions, their schemas and comments, and the rows of extension tables, which a
role that owns none of them may not write. Business schemas restore unchanged.

On a server without that template, callers keep their previous template and restore
everything, as before.
"""

import re

from psycopg import sql

TEMPLATE = "template_postgis"

_EXTENSION = re.compile(r"^\d+; \d+ \d+ EXTENSION - (\S+)(?: |$)")
_SCHEMA = re.compile(r"^\d+; \d+ \d+ SCHEMA - (\S+)(?: |$)")
_COMMENT = re.compile(r"^\d+; \d+ \d+ COMMENT - (SCHEMA|EXTENSION) (\S+)(?: |$)")
_ROWS = re.compile(r"^\d+; \d+ \d+ (?:TABLE DATA|SEQUENCE SET) (\S+) (\S+)(?: |$)")


def template_available(admin) -> bool:
    """True when the server has the PostGIS template marked as a template."""
    row = admin.execute(
        "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = %s AND datistemplate)",
        [TEMPLATE],
    ).fetchone()
    return bool(row[0])


def template_clause(admin, fallback: str | None = None) -> sql.Composable:
    """` TEMPLATE template_postgis` when available, else the fallback (or nothing)."""
    name = TEMPLATE if template_available(admin) else fallback
    if name is None:
        return sql.SQL("")
    return sql.SQL(" TEMPLATE {}").format(sql.Identifier(name))


def provided_objects(cursor) -> dict[str, set]:
    """What a database freshly created from the template already holds.

    Read from the new copy, never from the template itself: an open session on the
    template would block the next CREATE DATABASE that uses it.
    """
    cursor.execute("SELECT extname FROM pg_extension")
    extensions = {row[0] for row in cursor.fetchall()}
    cursor.execute("SELECT nspname FROM pg_namespace")
    schemas = {row[0] for row in cursor.fetchall()}
    cursor.execute(
        "SELECT n.nspname, c.relname FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "JOIN pg_depend d ON d.classid = 'pg_class'::regclass AND d.objid = c.oid "
        "AND d.deptype = 'e'"
    )
    members = {(schema, name) for schema, name in cursor.fetchall()}
    return {"extensions": extensions, "schemas": schemas, "members": members}


def restore_list(toc: str, provided: dict[str, set]) -> tuple[str, int]:
    """Filter a `pg_restore --list` output; returns the list and how many entries were skipped."""
    kept, skipped = [], 0
    for line in toc.splitlines():
        if _skip(line, provided):
            skipped += 1
        else:
            kept.append(line)
    return "\n".join(kept) + "\n", skipped


def _skip(line: str, provided: dict[str, set]) -> bool:
    if match := _EXTENSION.match(line):
        return match[1] in provided["extensions"]
    if match := _SCHEMA.match(line):
        return match[1] in provided["schemas"]
    if match := _COMMENT.match(line):
        kind = "extensions" if match[1] == "EXTENSION" else "schemas"
        return match[2] in provided[kind]
    if match := _ROWS.match(line):
        return (match[1], match[2]) in provided["members"]
    return False
