"""Copying chosen photos into the selection folder and removing them again."""

from __future__ import annotations

from pathlib import Path

from printpicker.export.copy import export_photo
from printpicker.export.naming import output_name
from printpicker.selection.sources import Source


class ExportsMixin:
    """Export tracking for :class:`~printpicker.selection.store.Selection`."""

    def exported_name(self, source: Source, rel_path: str) -> str | None:
        row = self.conn.execute(
            "SELECT exported_name FROM photos WHERE source_id = ? AND rel_path = ?",
            (source.id, rel_path),
        ).fetchone()
        return row[0] if row else None

    def exported_path(self, source: Source, rel_path: str) -> Path | None:
        name = self.exported_name(source, rel_path)
        return self.folder / name if name else None

    def export(self, source: Source, rel_path: str) -> Path:
        """Copy (or convert) a photo into the selection folder; no-op if already exported."""
        existing = self.exported_path(source, rel_path)
        if existing is not None and existing.exists():
            return existing
        src = source.path.joinpath(*rel_path.split("/"))
        result = export_photo(src, self.folder, output_name(source.name, rel_path))
        with self.conn:
            self.conn.execute(
                "INSERT INTO photos (source_id, rel_path, exported_name) VALUES (?, ?, ?) "
                "ON CONFLICT(source_id, rel_path) DO UPDATE SET "
                "exported_name = excluded.exported_name",
                (source.id, rel_path, result.path.name),
            )
        return result.path

    def unexport(self, source: Source, rel_path: str) -> None:
        """Remove the copy of a photo from the selection folder.

        The file is kept if another photo resolved to the very same file (identical content),
        so that photo's copy is not lost.
        """
        name = self.exported_name(source, rel_path)
        if name is None:
            return
        with self.conn:
            self.conn.execute(
                "UPDATE photos SET exported_name = NULL WHERE source_id = ? AND rel_path = ?",
                (source.id, rel_path),
            )
            shared = self.conn.execute(
                "SELECT 1 FROM photos WHERE exported_name = ? LIMIT 1", (name,)
            ).fetchone()
        if not shared:
            (self.folder / name).unlink(missing_ok=True)

    def exported_count(self) -> int:
        """Number of distinct files in the selection folder."""
        return self.conn.execute(
            "SELECT COUNT(DISTINCT exported_name) FROM photos WHERE exported_name IS NOT NULL"
        ).fetchone()[0]
