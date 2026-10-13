"""Selection screen: sources, analysis and the group-by-group review."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QItemSelectionModel, Qt, QTimer, QUrl, Signal
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
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from printpicker.core.grouping import Group, PhotoIndex
from printpicker.core.images import ImageLoadError
from printpicker.core.scanner import PhotoFile
from printpicker.core.similarity import Signature
from printpicker.selection import Selection, Source, SourceExistsError
from printpicker.selection.choices import first_unseen_group
from printpicker.ui import theme
from printpicker.ui.group_view import GroupView
from printpicker.ui.key_hints import KeyHints
from printpicker.ui.money import format_money
from printpicker.ui.settings import AppSettings
from printpicker.ui.settings_dialog import SettingsDialog
from printpicker.ui.thumbnails import ThumbnailLoader
from printpicker.ui.viewer import PhotoViewer
from printpicker.ui.workers import AnalysisThread

# Hamming distance on 64-bit hashes; above ~24 almost everything in a folder is "similar".
MAX_THRESHOLD = 24


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

    def __init__(
        self, folder: Path, settings: AppSettings | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.settings = settings or AppSettings()
        self.selection = Selection.open(folder)
        self.source: Source | None = None
        self.items: list[tuple[PhotoFile, Signature | None]] = []
        self.photo_index = PhotoIndex([])
        self.groups: list[Group] = []
        self.thread: AnalysisThread | None = None
        self.index = 0

        # Top bar.
        self.back_button = QPushButton(theme.icon("arrow-left"), self.tr("Selections"))
        theme.set_role(self.back_button, "flat")
        self.back_button.clicked.connect(self.close_selection)
        title = QLabel(f"<b>{self.selection.name}</b>")
        self.source_combo = QComboBox()
        self.source_combo.setMinimumWidth(220)
        self.source_combo.currentIndexChanged.connect(self._source_changed)
        self.add_source_button = QPushButton(theme.icon("folder-plus"), self.tr("Add source…"))
        self.add_source_button.clicked.connect(self.choose_source)
        top = QHBoxLayout()
        top.addWidget(self.back_button)
        top.addSpacing(12)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(QLabel(self.tr("Source:")))
        top.addWidget(self.source_combo)
        top.addWidget(self.add_source_button)
        self.settings_button = QPushButton(theme.icon("settings"), "")
        self.settings_button.setToolTip(self.tr("Settings…"))
        self.settings_button.setAccessibleName(self.tr("Settings…"))
        self.settings_button.clicked.connect(self.open_settings)
        top.addWidget(self.settings_button)

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
        self.relink_button = QPushButton(self.tr("The folder has moved: choose it…"))
        self.relink_button.clicked.connect(self.choose_relink)
        message_buttons = QWidget()
        row = QHBoxLayout(message_buttons)
        row.addWidget(self.retry_button)
        row.addWidget(self.relink_button)
        self.message_page = _centered(self.message_label, message_buttons)
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

    def choose_relink(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Where is “%1” now?").replace("%1", self.source.name)
        )
        if folder:
            self.relink(Path(folder))

    def relink(self, folder: Path, confirm: bool = True) -> bool:
        """Point the current source to ``folder``. Asks for confirmation when none of the
        photos seen before are there (probably the wrong folder)."""
        assert self.source is not None
        known = self.selection.known_photos(self.source)
        found = any(folder.joinpath(*rel.split("/")).exists() for rel in known[:200])
        if known and not found and confirm:
            answer = QMessageBox.question(
                self,
                self.tr("Different folder?"),
                self.tr(
                    "None of the photos analysed before are in “%1”.\n"
                    "Use this folder for “%2” anyway?"
                )
                .replace("%1", str(folder))
                .replace("%2", self.source.name),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return False
        try:
            self.source = self.selection.relink_source(self.source.id, folder)
        except SourceExistsError:
            QMessageBox.warning(
                self,
                self.tr("Source"),
                self.tr("This folder is already another source of the selection."),
            )
            return False
        self._source_changed()
        return True

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
                self.tr(
                    "The folder “%1” cannot be found.\n\n"
                    "Connect the drive and press Retry, or choose where the folder is now."
                ).replace("%1", str(self.source.path)),
                relink=True,
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

    def show_message(self, text: str, relink: bool = False) -> None:
        self.message_label.setText(text)
        self.relink_button.setVisible(relink)
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
            if self.source is not None and not self.source.is_available:
                self.thread = None
                self._source_changed()  # drive disconnected during the analysis
                return
            self.show_message(self.tr("The analysis failed:\n%1").replace("%1", message))

    def _on_analysed(self, items: list) -> None:
        if self.sender() is not self.thread:
            return
        self.items = items
        self.regroup()

    def regroup(self) -> None:
        """Group ``items`` from scratch (the slider then only regroups the same photos)."""
        self.photo_index = PhotoIndex(self.items)
        self.groups = self.photo_index.groups(self.selection.threshold)
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
        self.group_view.next_requested.connect(self.next_group)
        self.group_view.previous_requested.connect(self.previous_group)
        self.group_view.preview_requested.connect(self.open_preview)
        self.picked_label = QLabel()
        self.total_label = QLabel()
        self.next_button = QPushButton(
            theme.icon("arrow-right", theme.ON_ACCENT), self.tr("Next group")
        )
        self.next_button.setLayoutDirection(Qt.LayoutDirection.RightToLeft)  # arrow after text
        theme.set_role(self.next_button, "primary")
        self.next_button.setDefault(True)
        self.next_button.clicked.connect(self.next_group)

        self.previous_button = QPushButton(theme.icon("arrow-left"), self.tr("Previous group"))
        self.previous_button.setToolTip(self.tr("← or Backspace · your picks are kept"))
        self.next_button.setToolTip(self.tr("→ or Enter · your picks are kept"))
        self.help_label = KeyHints(
            [
                ([self.tr("Click"), self.tr("Space"), "1–9"], self.tr("pick")),
                (["A"], self.tr("all / none")),
                (["←", "→"], self.tr("groups")),
                (["↑", "↓", "Tab"], self.tr("photos")),
                (["F"], self.tr("preview")),
                (["C"], self.tr("crop")),
            ]
        )
        self.previous_button.clicked.connect(self.previous_group)

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, MAX_THRESHOLD)
        self.threshold_slider.setFixedWidth(160)
        self.threshold_slider.setValue(self.selection.threshold)
        self.threshold_slider.setToolTip(
            self.tr("How different two photos can be to end up in the same group")
        )
        self.threshold_slider.valueChanged.connect(lambda _v: self._regroup_timer.start())
        self._regroup_timer = QTimer(self)
        self._regroup_timer.setSingleShot(True)
        self._regroup_timer.setInterval(120)
        self._regroup_timer.timeout.connect(self._threshold_changed)
        similarity = QHBoxLayout()
        similarity.addWidget(QLabel(self.tr("Grouping: strict")))
        similarity.addWidget(self.threshold_slider)
        similarity.addWidget(QLabel(self.tr("loose")))

        bottom = QHBoxLayout()
        bottom.addWidget(self.previous_button)
        bottom.addSpacing(24)
        bottom.addWidget(self.picked_label)
        bottom.addSpacing(24)
        bottom.addWidget(self.total_label)
        bottom.addStretch()
        bottom.addLayout(similarity)
        bottom.addSpacing(24)
        bottom.addWidget(self.next_button)

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
            self.tr("<b>%1</b> — group %2 of %3 · %n photo(s)", "", len(group.photos))
            .replace("%1", group.folder or self.source.name)
            .replace("%2", str(index + 1))
            .replace("%3", str(len(self.groups)))
        )
        picked = self.selection.selected_photos(self.source)
        self.group_view.set_photos(list(group.photos), self._paths_for, picked)
        self.previous_button.setEnabled(index > 0)
        self.pages.setCurrentWidget(self.groups_page)
        self.group_view.setFocus()

    def save_group(self) -> bool:
        """Store the picks of the group on screen: picked photos are copied into the
        selection, unpicked ones removed. False if a copy failed."""
        assert self.source is not None
        group = self.groups[self.index]
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.selection.apply_choice(self.source, group, self.group_view.picked())
        except (OSError, ImageLoadError) as exc:
            QApplication.restoreOverrideCursor()
            if not self.source.is_available:
                self._source_changed()  # shows "folder not found" with retry / relink
                return False
            QMessageBox.warning(
                self,
                self.tr("Copy failed"),
                self.tr("Could not copy the photo:\n%1").replace("%1", str(exc)),
            )
            return False
        QApplication.restoreOverrideCursor()
        return True

    def next_group(self) -> None:
        if self.index < len(self.groups) and self.save_group():
            self.show_group(self.index + 1)

    def _build_end_page(self) -> QWidget:
        self.end_label = QLabel()
        self.end_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        open_button = QPushButton(
            theme.icon("folder-open", theme.ON_ACCENT), self.tr("Open the selection folder")
        )
        theme.set_role(open_button, "primary")
        open_button.setDefault(True)
        open_button.clicked.connect(self.open_folder)
        back_button = QPushButton(theme.icon("arrow-left"), self.tr("Previous group"))
        back_button.clicked.connect(self.previous_group)
        add_button = QPushButton(theme.icon("folder-plus"), self.tr("Add another source…"))
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
        """Photos in the selection and their estimated cost, e.g. "34 photos · ~10,20 €"."""
        count = self.selection.exported_count()
        price_list = self.settings.price_list
        estimate = price_list.estimate(count)
        text = self.tr("Photos to print: <b>%1</b>").replace("%1", str(count))
        if count:
            text += " · ~" + format_money(estimate.total, price_list.currency)
        self.total_label.setToolTip(
            self.tr("Estimate with “%1”: %2 per photo")
            .replace("%1", price_list.name)
            .replace("%2", format_money(estimate.unit_price, price_list.currency))
        )
        return text

    def open_settings(self) -> None:
        if SettingsDialog(self.settings, self).exec():
            self._update_counters()

    def open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.selection.folder)))

    def open_preview(self, row: int) -> None:
        photos = self.group_view.photo_model.photos
        if not photos:
            return
        viewer = PhotoViewer(
            photos,
            self._paths_for,
            lambda p: self.loader.cached(p.rel_path),
            self.group_view.picked(),
            row,
            self,
            show_crop=self.group_view.show_crop,
        )
        viewer.toggled.connect(self.group_view.toggle_row)
        viewer.crop_toggled.connect(self.group_view.set_show_crop)
        self.viewer = viewer
        viewer.showFullScreen()
        viewer.exec()
        self.viewer = None
        self.group_view.selectionModel().setCurrentIndex(
            self.group_view.photo_model.index(viewer.row),
            QItemSelectionModel.SelectionFlag.NoUpdate,
        )

    def _threshold_changed(self) -> None:
        """Regroup with the new threshold, staying on the photo currently shown."""
        self.selection.threshold = self.threshold_slider.value()
        if not self.items or self.source is None:
            return
        current = None
        if self.index < len(self.groups):
            row = max(self.group_view.currentIndex().row(), 0)
            current = self.groups[self.index].photos[row].rel_path
        self.groups = self.photo_index.groups(self.selection.threshold)
        if current is None:
            self.show_end()
            return
        index = next(
            i for i, g in enumerate(self.groups) if any(p.rel_path == current for p in g.photos)
        )
        self.show_group(index)

    def previous_group(self) -> None:
        """Go back, keeping the picks of the current group."""
        if self.index >= len(self.groups):
            if self.groups:
                self.show_group(len(self.groups) - 1)  # from the end page
        elif self.index > 0 and self.save_group():
            self.show_group(self.index - 1)

    def _update_counters(self) -> None:
        self.picked_label.setText(
            self.tr("Selected in this group: %1").replace("%1", str(len(self.group_view.picked())))
        )
        self.total_label.setText(self.summary_text())

    # Lifecycle ---------------------------------------------------------------------------

    def close_selection(self) -> None:
        self.cancel_analysis()
        self.loader.shutdown()
        self.selection.close()
        self.closed.emit()
