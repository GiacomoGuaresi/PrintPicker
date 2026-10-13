"""Start screen: create a new selection or open an existing one."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFile, QModelIndex, QPoint, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPalette
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from printpicker.selection import (
    InvalidSelectionError,
    Selection,
    SelectionExistsError,
    default_selection_name,
    list_selections,
    rename_selection,
    summarize,
)
from printpicker.ui import theme
from printpicker.ui.selection_cards import SelectionCardView
from printpicker.ui.settings import AppSettings
from printpicker.ui.settings_dialog import SettingsDialog
from printpicker.ui.thumbnails import ThumbnailLoader


def move_to_trash(path: Path) -> bool:
    return QFile.moveToTrash(str(path))


class StartScreen(QWidget):
    selection_opened = Signal(Path)

    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings

        title = QLabel("PrintPicker")
        font = title.font()
        font.setPointSize(font.pointSize() * 2)
        font.setBold(True)
        title.setFont(font)

        self.location = QLabel()
        self.location.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.location.setForegroundRole(QPalette.ColorRole.PlaceholderText)

        self.settings_button = QPushButton(theme.icon("settings"), self.tr("Settings…"))
        self.settings_button.clicked.connect(self.open_settings)

        heading = QVBoxLayout()
        heading.setSpacing(2)
        heading.addWidget(title)
        heading.addWidget(self.location)
        top = QHBoxLayout()
        top.addLayout(heading, 1)
        top.addWidget(self.settings_button, 0, Qt.AlignmentFlag.AlignTop)

        self.welcome = QLabel(
            self.tr(
                "<b>Welcome!</b> A print selection is a folder on your computer where the "
                "photos you choose from your archive are copied, ready to be sent to print. "
                "Create your first one to start."
            )
        )
        self.welcome.setWordWrap(True)

        self.loader = ThumbnailLoader(self)
        self.cards = SelectionCardView(self.loader)
        self.cards.open_requested.connect(self._open_index)
        self.cards.menu_requested.connect(self.show_menu)
        self.cards.rename_requested.connect(lambda _index: self.rename_selection())
        self.cards.delete_requested.connect(lambda _index: self.delete_selection())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 28, 40, 20)
        layout.setSpacing(16)
        layout.addLayout(top)
        layout.addWidget(self.welcome)
        layout.addWidget(self.cards, 1)

        self.refresh()

    def refresh(self, current: Path | None = None) -> None:
        base = self.settings.base_dir
        self.location.setText(self.tr("Selections in %1").replace("%1", str(base)))
        self.loader.reset()
        summaries = sorted(
            (summarize(f) for f in list_selections(base)), key=lambda s: s.last_used, reverse=True
        )
        self.cards.card_model.set_summaries(summaries, self.settings.price_list)
        self.welcome.setVisible(not summaries)
        model = self.cards.card_model
        rows = [s.folder for s in summaries]
        row = rows.index(current) + 1 if current in rows else (1 if summaries else 0)
        self.cards.setCurrentIndex(model.index(row))
        self.cards.setFocus()

    def selection_count(self) -> int:
        return len(self.cards.card_model.summaries)

    def selected_path(self) -> Path | None:
        summary = self.cards.card_model.summary(self.cards.currentIndex())
        return summary.folder if summary else None

    def _open_index(self, index: QModelIndex) -> None:
        summary = self.cards.card_model.summary(index)
        if summary is None:
            self.new_selection()
        else:
            self.selection_opened.emit(summary.folder)

    def menu_actions(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction(self.tr("Open"), self._open_current)
        menu.addAction(self.tr("Open folder"), self.open_folder)
        menu.addSeparator()
        menu.addAction(self.tr("Rename…"), self.rename_selection)
        menu.addAction(self.tr("Delete…"), self.delete_selection)
        return menu

    def show_menu(self, _index: QModelIndex, pos: QPoint) -> None:
        self.menu_actions().exec(pos)

    def _open_current(self) -> None:
        self._open_index(self.cards.currentIndex())

    def open_folder(self) -> None:
        path = self.selected_path()
        if path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def rename_selection(self) -> None:
        path = self.selected_path()
        if path is None:
            return
        name = path.name
        while True:
            name, ok = QInputDialog.getText(
                self, self.tr("Rename selection"), self.tr("New name:"), text=name
            )
            if not ok:
                return
            try:
                new_path = rename_selection(path, name)
            except SelectionExistsError:
                message = self.tr("A selection with this name already exists.")
            except InvalidSelectionError:
                message = self.tr("This name cannot be used for a folder.")
            except OSError as exc:
                message = self.tr("Could not rename the selection: %1").replace("%1", str(exc))
            else:
                self.refresh(current=new_path)
                return
            QMessageBox.warning(self, self.tr("Rename selection"), message)

    def shutdown(self) -> None:
        self.loader.shutdown()

    def new_selection(self) -> None:
        name = default_selection_name(self.tr("Print"))
        while True:
            name, ok = QInputDialog.getText(
                self, self.tr("New selection"), self.tr("Name of the selection:"), text=name
            )
            if not ok:
                return
            path = self.create_selection(name)
            if path is not None:
                self.selection_opened.emit(path)
                return

    def create_selection(self, name: str) -> Path | None:
        """Create the selection folder; shows an error and returns None if it is not possible."""
        try:
            base = self.settings.base_dir
            base.mkdir(parents=True, exist_ok=True)
            with Selection.create(base, name) as selection:
                return selection.folder
        except SelectionExistsError:
            message = self.tr("A selection with this name already exists.")
        except InvalidSelectionError:
            message = self.tr("This name cannot be used for a folder.")
        except OSError as exc:
            message = self.tr("Could not create the selection: %1").replace("%1", str(exc))
        QMessageBox.warning(self, self.tr("New selection"), message)
        return None

    def open_settings(self) -> None:
        if SettingsDialog(self.settings, self).exec():
            self.refresh()

    def delete_selection(self) -> None:
        path = self.selected_path()
        if path is None:
            return
        answer = QMessageBox.question(
            self,
            self.tr("Delete selection"),
            self.tr(
                "Move the selection “%1” and the photos it contains to the trash?\n\n"
                "The original photos in your archive are not touched."
            ).replace("%1", path.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if not move_to_trash(path):
            QMessageBox.warning(
                self,
                self.tr("Delete selection"),
                self.tr("Could not move “%1” to the trash.").replace("%1", path.name),
            )
        self.refresh()
