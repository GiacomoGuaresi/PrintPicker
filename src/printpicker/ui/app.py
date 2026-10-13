"""Application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from printpicker.about import APP_NAME, __version__
from printpicker.ui.main_window import MainWindow
from printpicker.ui.theme import apply_theme

PACKAGE_DIR = Path(__file__).resolve().parent.parent
I18N_DIR = PACKAGE_DIR / "i18n"
ICON_PATH = PACKAGE_DIR / "resources" / "icon.png"


def install_translations(app: QApplication, locale: QLocale | None = None) -> list[QTranslator]:
    """Load PrintPicker's and Qt's own translations for ``locale`` (default: the system's).

    English is the source language: without a matching translation the texts stay English.
    """
    locale = locale or QLocale.system()
    translators = []
    qt_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    for name, directory in (("qtbase", qt_dir), ("printpicker", str(I18N_DIR))):
        translator = QTranslator(app)
        if translator.load(locale, name, "_", directory):
            app.installTranslator(translator)
            translators.append(translator)
    return translators


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    apply_theme(app)
    return app


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    app = create_application(argv)
    if "--self-test" in argv:
        from printpicker.ui.selftest import run_self_test

        return run_self_test(app)
    install_translations(app)
    window = MainWindow()
    window.show()
    window.schedule_update_check()
    return app.exec()
