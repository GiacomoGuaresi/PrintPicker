"""Choices made in each group, and where to resume."""

from __future__ import annotations

from collections.abc import Collection, Sequence

from printpicker.core.grouping import DEFAULT_THRESHOLD, Group
from printpicker.selection.sources import Source


def first_unseen_group(groups: Sequence[Group], seen: Collection[str]) -> int:
    """Index of the first group with a photo not seen yet; ``len(groups)`` if all were seen."""
    for i, group in enumerate(groups):
        if any(p.rel_path not in seen for p in group.photos):
            return i
    return len(groups)


class ChoicesMixin:
    """Choices and progress for :class:`~printpicker.selection.store.Selection`."""

    def apply_choice(self, source: Source, group: Group, selected: Collection[str]) -> None:
        """Confirm a group: every photo becomes seen; ``selected`` ones are exported and the
        others removed from the selection folder (if they had been exported before)."""
        for photo in group.photos:
            is_selected = photo.rel_path in selected
            # Copy first: if it fails (drive disconnected...) the photo is not marked as seen,
            # so the group is proposed again.
            if is_selected:
                self.export(source, photo.rel_path)
            else:
                self.unexport(source, photo.rel_path)
            with self.conn:
                self.conn.execute(
                    "INSERT INTO photos (source_id, rel_path, seen, selected) VALUES (?, ?, 1, ?) "
                    "ON CONFLICT(source_id, rel_path) DO UPDATE SET "
                    "seen = 1, selected = excluded.selected",
                    (source.id, photo.rel_path, int(is_selected)),
                )

    def _paths_where(self, source: Source, column: str) -> set[str]:
        rows = self.conn.execute(
            f"SELECT rel_path FROM photos WHERE source_id = ? AND {column} = 1", (source.id,)
        )
        return {r[0] for r in rows}

    def seen_photos(self, source: Source) -> set[str]:
        return self._paths_where(source, "seen")

    def selected_photos(self, source: Source) -> set[str]:
        return self._paths_where(source, "selected")

    def selected_count(self) -> int:
        """Photos picked for print, across all sources."""
        return self.conn.execute("SELECT COUNT(*) FROM photos WHERE selected = 1").fetchone()[0]

    @property
    def threshold(self) -> int:
        return int(self.get_meta("threshold", str(DEFAULT_THRESHOLD)))

    @threshold.setter
    def threshold(self, value: int) -> None:
        self.set_meta("threshold", str(int(value)))
