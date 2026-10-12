"""Selection screen: sources, analysis and the group-by-group review."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from printpicker.core.grouping import Group, group_photos
from printpicker.core.scanner import PhotoFile
from printpicker.selection import Selection, Source, SourceExistsError
from printpicker.ui.workers import AnalysisThread


def _centered(*widgets: QWidget) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.addStretch()
    for w in widgets:
        layout.addWidget(w, 0, Qt.AlignmentFlag.AlignHCenter)
    layout.addStretch()
    return page


class SessionScreen(QWidget):
    closed = Signal()

    def __init__(self, folder: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.selection = Selection.open(folder)
        self.source: Source | None = None
        self.items: list[tuple[PhotoFile, int | None]] = []
        self.groups: list[Group] = []
        self.thread: AnalysisThread | None = None

        # Top bar.
        self.back_button = QPushButton(self.tr("← Selections"))
        self.back_button.clicked.connect(self.close_selection)
        title = QLabel(f"<b>{self.selection.name}</b>")
        self.source_combo = QComboBox()
        self.source_combo.setMinimumWidth(220)
        self.source_combo.currentIndexChanged.connect(self._source_changed)
        self.add_source_button = QPushButton(self.tr("Add source…"))
        self.add_source_button.clicked.connect(self.choose_source)
        top = QHBoxLayout()
        top.addWidget(self.back_button)
        top.addSpacing(12)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(QLabel(self.tr("Source:")))
        top.addWidget(self.source_combo)
        top.addWidget(self.add_source_button)

        # Pages.
        self.pages = QStackedWidget()
        self.empty_page = _centered(
            QLabel(self.tr("Add a folder of your photo archive to start choosing photos.")),
        )
        self.progress_label = QLabel()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumWidth(400)
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.clicked.connect(self._cancel_clicked)
        self.progress_page = _centered(self.progress_label, self.progress_bar, self.cancel_button)
        self.message_label = QLabel()
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.retry_button = QPushButton(self.tr("Retry"))
        self.retry_button.clicked.connect(self._source_changed)
        self.message_page = _centered(self.message_label, self.retry_button)
        self.groups_page = _centered(QLabel())
        for page in (self.empty_page, self.progress_page, self.message_page, self.groups_page):
            self.pages.addWidget(page)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.pages, 1)

        self._reload_sources()

    # Sources -----------------------------------------------------------------------------

    def _reload_sources(self, select_id: int | None = None) -> None:
        sources = self.selection.sources()
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        for s in sources:
            self.source_combo.addItem(s.name, s.id)
        self.source_combo.blockSignals(False)
        self.source_combo.setEnabled(bool(sources))
        if not sources:
            self.pages.setCurrentWidget(self.empty_page)
            return
        index = self.source_combo.findData(select_id) if select_id is not None else 0
        self.source_combo.setCurrentIndex(max(index, 0))
        self._source_changed()

    def choose_source(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self.tr("Choose a folder of photos"))
        if folder:
            self.add_source(Path(folder))

    def add_source(self, folder: Path) -> None:
        try:
            source = self.selection.add_source(folder)
        except SourceExistsError:
            existing = next(s for s in self.selection.sources() if s.path == folder.resolve())
            source = existing
        self._reload_sources(source.id)

    def _source_changed(self, *_args) -> None:
        source_id = self.source_combo.currentData()
        if source_id is None:
            return
        self.cancel_analysis()
        self.source = self.selection.source(source_id)
        if not self.source.is_available:
            self.show_message(
                self.tr("The folder “%1” cannot be found.\nIs the drive connected?").replace(
                    "%1", str(self.source.path)
                )
            )
            return
        self.start_analysis()

    # Analysis ----------------------------------------------------------------------------

    def start_analysis(self) -> None:
        assert self.source is not None
        self.progress_label.setText(self.tr("Analysing “%1”…").replace("%1", self.source.name))
        self.progress_bar.setRange(0, 0)
        self.pages.setCurrentWidget(self.progress_page)
        self.add_source_button.setEnabled(False)
        thread = AnalysisThread(self.selection.folder, self.source.id, self)
        thread.progress.connect(self._on_progress)
        thread.analysed.connect(self._on_analysed)
        thread.failed.connect(self._on_failed)
        thread.finished.connect(self._on_thread_finished)
        self.thread = thread
        thread.start()

    def cancel_analysis(self) -> None:
        if self.thread is not None:
            self.thread.cancel()
            self.thread.wait()
            self.thread = None
            self.add_source_button.setEnabled(True)

    def _cancel_clicked(self) -> None:
        self.cancel_analysis()
        self.show_message(self.tr("Analysis interrupted. Photos analysed so far are kept."))

    def show_message(self, text: str) -> None:
        self.message_label.setText(text)
        self.pages.setCurrentWidget(self.message_page)

    def _on_progress(self, done: int, total: int) -> None:
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(done)
        self.progress_bar.setFormat(
            self.tr("%1 of %2 photos").replace("%1", str(done)).replace("%2", str(total))
        )

    def _on_thread_finished(self) -> None:
        if self.sender() is self.thread:
            self.thread = None
            self.add_source_button.setEnabled(True)

    def _on_failed(self, message: str) -> None:
        if self.sender() is self.thread:
            self.show_message(self.tr("The analysis failed:\n%1").replace("%1", message))

    def _on_analysed(self, items: list) -> None:
        if self.sender() is not self.thread:
            return
        self.items = items
        self.regroup()

    def regroup(self) -> None:
        self.groups = group_photos(self.items, self.selection.threshold)
        self.show_groups()

    def show_groups(self) -> None:
        label = self.groups_page.findChild(QLabel)
        label.setText(
            self.tr("%1 photos in %2 groups")
            .replace("%1", str(len(self.items)))
            .replace("%2", str(len(self.groups)))
        )
        self.pages.setCurrentWidget(self.groups_page)

    # Lifecycle ---------------------------------------------------------------------------

    def close_selection(self) -> None:
        self.cancel_analysis()
        self.selection.close()
        self.closed.emit()
