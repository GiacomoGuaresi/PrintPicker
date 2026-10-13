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

    -- Source folders. ``path`` is the last known absolute location (it can change when a drive
    -- is remounted); ``name`` is fixed at creation and used for output file prefixes.
    CREATE TABLE sources (
        id       INTEGER PRIMARY KEY,
        path     TEXT NOT NULL UNIQUE,
        name     TEXT NOT NULL,
        added_at TEXT NOT NULL
    );

    -- Photos found in a source, identified by their POSIX path relative to the source root.
    -- ``size`` / ``mtime_ns`` detect changed files; ``hashed`` tells "not computed yet" apart
    -- from "unreadable" (hash NULL in both cases).
    CREATE TABLE photos (
        id        INTEGER PRIMARY KEY,
        source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
        rel_path  TEXT NOT NULL,
        size      INTEGER,
        mtime_ns  INTEGER,
        hash      INTEGER,
        hashed    INTEGER NOT NULL DEFAULT 0,
        -- Choices: ``seen`` once its group was confirmed, ``selected`` if picked for print.
        -- Stored per photo (not per group) because groups change with the threshold.
        seen      INTEGER NOT NULL DEFAULT 0,
        selected  INTEGER NOT NULL DEFAULT 0,
        -- File name of the copy in the selection folder, NULL when not exported.
        exported_name TEXT,
        UNIQUE (source_id, rel_path)
    );
    """,
    """
    -- Image embedding (float16), NULL when not computed: photos analysed before, or without
    -- the model, or unreadable (hash NULL too).
    ALTER TABLE photos ADD COLUMN embedding BLOB;
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
