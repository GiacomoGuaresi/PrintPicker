"""Main window: hosts the start screen and the selection screen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QStackedWidget

from printpicker.about import APP_NAME
from printpicker.ui.session_screen import SessionScreen
from printpicker.ui.settings import AppSettings
from printpicker.ui.start_screen import StartScreen


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
        self.session: SessionScreen | None = None

    def open_selection(self, folder: Path) -> None:
        self.current_selection = folder
        self.setWindowTitle(f"{folder.name} — {APP_NAME}")
        self.session = SessionScreen(folder, self.settings)
        self.session.closed.connect(self.show_start)
        self.stack.addWidget(self.session)
        self.stack.setCurrentWidget(self.session)

    def show_start(self) -> None:
        self.current_selection = None
        self.setWindowTitle(APP_NAME)
        self.start_screen.refresh()
        self.stack.setCurrentWidget(self.start_screen)
        if self.session is not None:
            self.stack.removeWidget(self.session)
            self.session.deleteLater()
            self.session = None

    def closeEvent(self, event) -> None:
        if self.session is not None:
            self.session.close_selection()
        self.start_screen.shutdown()
        super().closeEvent(event)
