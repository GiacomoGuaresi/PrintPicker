"""SQLite schema of a selection database, with forward-only migrations."""

from __future__ import annotations

import sqlite3

# Each entry migrates from version ``index`` to ``index + 1``.
MIGRATIONS: list[str] = [
    """
    CREATE TABLE meta (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """,
]

SCHEMA_VERSION = len(MIGRATIONS)


class SchemaTooNewError(Exception):
    """The database was written by a newer PrintPicker."""


def migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise SchemaTooNewError(f"schema version {version} > supported {SCHEMA_VERSION}")
    for target in range(version, SCHEMA_VERSION):
        with conn:
            conn.executescript(MIGRATIONS[target])
            conn.execute(f"PRAGMA user_version = {target + 1}")
