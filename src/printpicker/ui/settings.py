"""Global application settings (stored with QSettings in the user's config folder)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths

APP_FOLDER = "PrintPicker"


def default_base_dir() -> Path:
    documents = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    return Path(documents or Path.home()) / APP_FOLDER


class AppSettings:
    def __init__(self, settings: QSettings | None = None) -> None:
        self._s = settings or QSettings()

    @property
    def base_dir(self) -> Path:
        value = self._s.value("selections/base_dir")
        return Path(value) if value else default_base_dir()

    @base_dir.setter
    def base_dir(self, path: Path) -> None:
        self._s.setValue("selections/base_dir", str(path))
