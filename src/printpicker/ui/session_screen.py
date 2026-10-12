"""Selection screen: sources, analysis and the group-by-group review."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from printpicker.core.grouping import Group, group_photos
from printpicker.core.images import ImageLoadError
from printpicker.core.scanner import PhotoFile
from printpicker.selection import Selection, Source, SourceExistsError
from printpicker.selection.choices import first_unseen_group
from printpicker.ui.group_view import GroupView
from printpicker.ui.thumbnails import ThumbnailLoader
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
        self.index = 0

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
        self.groups_page = self._build_groups_page()
        self.end_page = self._build_end_page()
        pages = (self.empty_page, self.progress_page, self.message_page, self.groups_page)
        for page in (*pages, self.end_page):
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
        if select_id is None:
            last = self.selection.get_meta("last_source")
            select_id = int(last) if last else None
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
        self.loader.reset()
        self.source = self.selection.source(source_id)
        self.selection.set_meta("last_source", str(source_id))
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
        """Resume from the first group with photos not reviewed yet."""
        assert self.source is not None
        self.show_group(first_unseen_group(self.groups, self.selection.seen_photos(self.source)))

    # Group review ------------------------------------------------------------------------

    def _build_groups_page(self) -> QWidget:
        self.loader = ThumbnailLoader(self)
        self.group_title = QLabel()
        self.group_view = GroupView(self.loader)
        self.group_view.picked_changed.connect(self._update_counters)
        self.group_view.confirm_requested.connect(self.confirm_group)
        self.group_view.back_requested.connect(self.previous_group)
        self.picked_label = QLabel()
        self.total_label = QLabel()
        self.confirm_button = QPushButton(self.tr("Confirm and continue →"))
        self.confirm_button.setDefault(True)
        self.confirm_button.clicked.connect(self.confirm_group)

        self.previous_button = QPushButton(self.tr("← Previous group"))
        self.previous_button.setToolTip(self.tr("Backspace"))
        self.confirm_button.setToolTip(self.tr("Enter"))
        self.help_label = QLabel(
            self.tr("Arrows: move · Space or 1–9: pick · Enter: confirm · Backspace: back")
        )
        self.help_label.setEnabled(False)
        self.previous_button.clicked.connect(self.previous_group)

        bottom = QHBoxLayout()
        bottom.addWidget(self.previous_button)
        bottom.addSpacing(24)
        bottom.addWidget(self.picked_label)
        bottom.addSpacing(24)
        bottom.addWidget(self.total_label)
        bottom.addStretch()
        bottom.addWidget(self.confirm_button)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.group_title)
        layout.addWidget(self.group_view, 1)
        layout.addLayout(bottom)
        layout.addWidget(self.help_label, 0, Qt.AlignmentFlag.AlignHCenter)
        return page

    def _paths_for(self, photo: PhotoFile) -> tuple[Path, Path]:
        assert self.source is not None
        return (
            photo.absolute(self.source.path),
            self.selection.thumb_path(self.source, photo.rel_path),
        )

    def show_group(self, index: int) -> None:
        assert self.source is not None
        self.index = index
        if index >= len(self.groups):
            self.show_end()
            return
        group = self.groups[index]
        self.group_title.setText(
            self.tr("<b>%1</b> — group %2 of %3 · %4 photo(s)")
            .replace("%1", group.folder or self.source.name)
            .replace("%2", str(index + 1))
            .replace("%3", str(len(self.groups)))
            .replace("%4", str(len(group.photos)))
        )
        picked = self.selection.selected_photos(self.source)
        self.group_view.set_photos(list(group.photos), self._paths_for, picked)
        self.previous_button.setEnabled(index > 0)
        self.pages.setCurrentWidget(self.groups_page)
        self.group_view.setFocus()

    def confirm_group(self) -> None:
        assert self.source is not None
        group = self.groups[self.index]
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.selection.apply_choice(self.source, group, self.group_view.picked())
        except (OSError, ImageLoadError) as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(
                self,
                self.tr("Copy failed"),
                self.tr("Could not copy the photo:\n%1").replace("%1", str(exc)),
            )
            return
        QApplication.restoreOverrideCursor()
        self.show_group(self.index + 1)

    def _build_end_page(self) -> QWidget:
        self.end_label = QLabel()
        self.end_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        open_button = QPushButton(self.tr("Open the selection folder"))
        open_button.setDefault(True)
        open_button.clicked.connect(self.open_folder)
        back_button = QPushButton(self.tr("← Previous group"))
        back_button.clicked.connect(self.previous_group)
        add_button = QPushButton(self.tr("Add another source…"))
        add_button.clicked.connect(self.choose_source)
        buttons = QWidget()
        row = QHBoxLayout(buttons)
        for b in (back_button, add_button, open_button):
            row.addWidget(b)
        return _centered(self.end_label, buttons)

    def show_end(self) -> None:
        assert self.source is not None
        self.index = len(self.groups)
        self.end_label.setText(
            self.tr("<h2>Done!</h2>All the photos of “%1” have been reviewed.<br><br>%2")
            .replace("%1", self.source.name)
            .replace("%2", self.summary_text())
        )
        self.pages.setCurrentWidget(self.end_page)

    def summary_text(self) -> str:
        return self.tr("Photos to print: <b>%1</b>").replace(
            "%1", str(self.selection.selected_count())
        )

    def open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.selection.folder)))

    def previous_group(self) -> None:
        """Go back without saving the current group; its previous choice is kept."""
        if self.index > 0:
            self.show_group(min(self.index, len(self.groups)) - 1)

    def _update_counters(self) -> None:
        self.picked_label.setText(
            self.tr("Selected in this group: %1").replace("%1", str(len(self.group_view.picked())))
        )
        self.total_label.setText(
            self.tr("Photos to print: %1").replace("%1", str(self.selection.selected_count()))
        )

    # Lifecycle ---------------------------------------------------------------------------

    def close_selection(self) -> None:
        self.cancel_analysis()
        self.loader.shutdown()
        self.selection.close()
        self.closed.emit()
