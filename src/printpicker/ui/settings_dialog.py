"""Settings dialog: where selections are stored and the print price list."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from printpicker.ui.settings import AppSettings, default_base_dir


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(self.tr("Settings"))
        self.setMinimumWidth(560)

        self.base_dir_edit = QLineEdit(str(settings.base_dir))
        browse = QPushButton(self.tr("Browse…"))
        browse.clicked.connect(self._browse)
        reset = QPushButton(self.tr("Default"))
        reset.clicked.connect(lambda: self.base_dir_edit.setText(str(default_base_dir())))
        row = QHBoxLayout()
        row.addWidget(self.base_dir_edit, 1)
        row.addWidget(browse)
        row.addWidget(reset)
        hint = QLabel(self.tr("New selections are created here. Existing ones are not moved."))
        hint.setEnabled(False)

        form = QFormLayout()
        form.addRow(self.tr("Selections folder:"), row)
        form.addRow("", hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        self.body = QVBoxLayout(self)
        self.body.addLayout(form)
        self.body.addWidget(buttons)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Selections folder"), self.base_dir_edit.text()
        )
        if folder:
            self.base_dir_edit.setText(folder)

    def accept(self) -> None:
        text = self.base_dir_edit.text().strip()
        if text:
            self.settings.base_dir = Path(text)
        super().accept()
