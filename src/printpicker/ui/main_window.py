"""Main window: hosts the start screen and the selection screen."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QMainWindow, QStackedWidget

from printpicker import __version__

APP_NAME = "PrintPicker"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 800)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        placeholder = QLabel(f"{APP_NAME} {__version__}")
        self.stack.addWidget(placeholder)
