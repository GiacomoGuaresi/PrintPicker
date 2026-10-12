"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from printpicker import __version__
from printpicker.ui.main_window import APP_NAME, MainWindow


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationVersion(__version__)
    return app


def main(argv: list[str] | None = None) -> int:
    app = create_application(argv)
    window = MainWindow()
    window.show()
    return app.exec()
