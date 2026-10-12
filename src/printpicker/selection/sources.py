"""Source folders of a selection."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path


class SourceExistsError(Exception):
    """The folder is already a source of this selection."""


@dataclass(frozen=True)
class Source:
    id: int
    path: Path
    name: str

    @property
    def is_available(self) -> bool:
        """False when the folder is missing, e.g. the drive is disconnected or remounted."""
        try:
            return self.path.is_dir()
        except OSError:
            return False


def source_name(path: Path) -> str:
    """Display name of a source folder; a drive root (``E:\\``) is named after its drive."""
    if path.name:
        return path.name
    return path.drive.rstrip(":\\/") or str(path)


class SourcesMixin:
    """Source management for :class:`~printpicker.selection.store.Selection`."""

    def sources(self) -> list[Source]:
        rows = self.conn.execute("SELECT id, path, name FROM sources ORDER BY id").fetchall()
        return [Source(id_, Path(path), name) for id_, path, name in rows]

    def source(self, source_id: int) -> Source:
        row = self.conn.execute(
            "SELECT id, path, name FROM sources WHERE id = ?", (source_id,)
        ).fetchone()
        if row is None:
            raise KeyError(source_id)
        return Source(row[0], Path(row[1]), row[2])

    def add_source(self, path: Path) -> Source:
        path = Path(path).resolve()
        if any(s.path == path for s in self.sources()):
            raise SourceExistsError(str(path))
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO sources (path, name, added_at) VALUES (?, ?, ?)",
                (str(path), source_name(path), dt.datetime.now().isoformat(timespec="seconds")),
            )
        return self.source(cur.lastrowid)

    def relink_source(self, source_id: int, new_path: Path) -> Source:
        """Point a source to its new location. Photos keep their relative paths, so progress
        and choices stay valid."""
        new_path = Path(new_path).resolve()
        if any(s.path == new_path and s.id != source_id for s in self.sources()):
            raise SourceExistsError(str(new_path))
        with self.conn:
            self.conn.execute(
                "UPDATE sources SET path = ? WHERE id = ?", (str(new_path), source_id)
            )
        return self.source(source_id)
