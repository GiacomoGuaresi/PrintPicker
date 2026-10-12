"""Main window: hosts the start screen and the selection screen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QLabel, QMainWindow, QStackedWidget

from printpicker.ui.settings import AppSettings
from printpicker.ui.start_screen import StartScreen

APP_NAME = "PrintPicker"


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings | None = None) -> None:
        super().__init__()
        self.settings = settings or AppSettings()
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 800)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.start_screen = StartScreen(self.settings)
        self.start_screen.selection_opened.connect(self.open_selection)
        self.stack.addWidget(self.start_screen)
        self.current_selection: Path | None = None

    def open_selection(self, folder: Path) -> None:
        self.current_selection = folder
        self.setWindowTitle(f"{folder.name} — {APP_NAME}")
        placeholder = QLabel(str(folder))
        self.stack.addWidget(placeholder)
        self.stack.setCurrentWidget(placeholder)
