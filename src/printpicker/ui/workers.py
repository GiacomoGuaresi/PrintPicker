"""Background work: analysing a source without blocking the interface."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from printpicker.selection import Selection


class AnalysisThread(QThread):
    """Scans and hashes a source using its own database connection.

    Emits ``progress(done, total)`` while working and ``analysed(items)`` with the list of
    ``(PhotoFile, hash)`` at the end (unless cancelled), or ``failed(message)``.
    """

    progress = Signal(int, int)
    analysed = Signal(object)
    failed = Signal(str)

    def __init__(self, selection_folder: Path, source_id: int, parent=None) -> None:
        super().__init__(parent)
        self.selection_folder = selection_folder
        self.source_id = source_id
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def run(self) -> None:
        try:
            with Selection.open(self.selection_folder) as selection:
                items = selection.analyze_source(
                    selection.source(self.source_id),
                    progress=self.progress.emit,
                    cancelled=lambda: self._cancelled,
                )
        except Exception as exc:  # reported to the UI, never crash the thread
            self.failed.emit(str(exc))
            return
        if not self._cancelled:
            self.analysed.emit(items)
