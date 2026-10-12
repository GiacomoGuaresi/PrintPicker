"""Start screen: create a new selection or open an existing one."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFile, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from printpicker.core.formats import is_supported
from printpicker.selection import (
    DATA_DIR,
    InvalidSelectionError,
    Selection,
    SelectionExistsError,
    default_selection_name,
    list_selections,
)
from printpicker.ui.settings import AppSettings

PATH_ROLE = Qt.ItemDataRole.UserRole


def photo_count(folder: Path) -> int:
    try:
        return sum(1 for p in folder.iterdir() if p.is_file() and is_supported(p.name))
    except OSError:
        return 0


def move_to_trash(path: Path) -> bool:
    return QFile.moveToTrash(str(path))


def last_used(folder: Path) -> float:
    try:
        return (folder / DATA_DIR / "selection.db").stat().st_mtime
    except OSError:
        return 0.0


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

        self.list = QListWidget()
        self.list.setSpacing(4)
        self.list.itemActivated.connect(self._open_item)
        self.list.currentItemChanged.connect(self._update_buttons)

        self.new_button = QPushButton(self.tr("New selection…"))
        self.new_button.setDefault(True)
        self.new_button.clicked.connect(self.new_selection)
        self.open_button = QPushButton(self.tr("Open"))
        self.open_button.clicked.connect(lambda: self._open_item(self.list.currentItem()))

        self.delete_button = QPushButton(self.tr("Delete…"))
        self.delete_button.clicked.connect(self.delete_selection)

        buttons = QHBoxLayout()
        buttons.addWidget(self.new_button)
        buttons.addStretch()
        buttons.addWidget(self.delete_button)
        buttons.addWidget(self.open_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 32, 48, 32)
        layout.addWidget(title)
        layout.addWidget(QLabel(self.tr("Print selections")))
        layout.addWidget(self.location)
        layout.addWidget(self.list, 1)
        layout.addLayout(buttons)

        self.refresh()

    def refresh(self) -> None:
        base = self.settings.base_dir
        self.location.setText(str(base))
        self.list.clear()
        for folder in sorted(list_selections(base), key=last_used, reverse=True):
            n = photo_count(folder)
            item = QListWidgetItem(self.tr("%1  ·  %n photo(s)", "", n).replace("%1", folder.name))
            item.setData(PATH_ROLE, folder)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)
        self._update_buttons()

    def selected_path(self) -> Path | None:
        item = self.list.currentItem()
        return item.data(PATH_ROLE) if item else None

    def _update_buttons(self, *_args) -> None:
        has_item = self.list.currentItem() is not None
        self.open_button.setEnabled(has_item)
        self.delete_button.setEnabled(has_item)

    def _open_item(self, item: QListWidgetItem | None) -> None:
        if item is not None:
            self.selection_opened.emit(item.data(PATH_ROLE))

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
