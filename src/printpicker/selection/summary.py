"""At-a-glance data about a selection, for the start screen."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from printpicker.selection.schema import SchemaTooNewError
from printpicker.selection.store import DATA_DIR, DB_NAME, InvalidSelectionError, Selection

COVER_SIZE = 4


@dataclass(frozen=True)
class SelectionSummary:
    folder: Path
    photo_count: int = 0
    source_count: int = 0
    last_used: float = 0.0
    # (exported file, cached thumbnail) of the first chosen photos.
    cover: list[tuple[Path, Path]] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.folder.name


def last_used(folder: Path) -> float:
    """Last time the selection was changed: the newest of its database files."""
    db = Path(folder) / DATA_DIR / DB_NAME
    times = []
    for path in (db, db.with_name(DB_NAME + "-wal")):
        try:
            times.append(path.stat().st_mtime)
        except OSError:
            pass
    return max(times, default=0.0)


def summarize(folder: Path) -> SelectionSummary:
    """Summary of a selection; an unreadable selection gives an empty summary."""
    folder = Path(folder)
    used = last_used(folder)
    try:
        with Selection.open(folder) as selection:
            sources = {s.id: s for s in selection.sources()}
            rows = selection.conn.execute(
                "SELECT source_id, rel_path, exported_name FROM photos "
                "WHERE exported_name IS NOT NULL ORDER BY id"
            ).fetchall()
            cover: list[tuple[Path, Path]] = []
            names: set[str] = set()
            for source_id, rel_path, name in rows:
                if name in names:
                    continue
                names.add(name)
                if len(cover) < COVER_SIZE:
                    thumb = selection.thumb_path(sources[source_id], rel_path)
                    cover.append((folder / name, thumb))
            return SelectionSummary(folder, len(names), len(sources), used, cover)
    except (sqlite3.Error, OSError, InvalidSelectionError, SchemaTooNewError):
        return SelectionSummary(folder, last_used=used)
