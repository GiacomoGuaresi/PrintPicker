"""Main window: hosts the start screen and the selection screen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import QMainWindow, QMenu, QStackedWidget

from printpicker import about
from printpicker.about import APP_NAME
from printpicker.ui import theme
from printpicker.ui.about_dialog import AboutDialog, open_url
from printpicker.ui.session_screen import SessionScreen
from printpicker.ui.settings import AppSettings
from printpicker.ui.start_screen import StartScreen


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings | None = None) -> None:
        super().__init__()
        self.settings = settings or AppSettings()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(900, 600)
        if not self.restoreGeometry(self.settings.window_geometry):
            self.resize(1280, 820)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.start_screen = StartScreen(self.settings)
        self.start_screen.selection_opened.connect(self.open_selection)
        self.stack.addWidget(self.start_screen)
        self.current_selection: Path | None = None
        self.session: SessionScreen | None = None
        self._build_menus()

    # Menus -------------------------------------------------------------------------------

    def _action(
        self,
        menu: QMenu,
        text: str,
        slot,
        shortcut: QKeySequence | QKeySequence.StandardKey | None = None,
        role: QAction.MenuRole = QAction.MenuRole.NoRole,
        icon: str | None = None,
    ) -> QAction:
        action = QAction(text, self)
        if icon:
            action.setIcon(theme.icon(icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.setMenuRole(role)  # on macOS, roles move About / Settings / Quit to the app menu
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def _build_menus(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu(self.tr("&File"))
        self.new_action = self._action(
            file_menu,
            self.tr("New selection…"),
            self.new_selection,
            QKeySequence.StandardKey.New,
            icon="plus",
        )
        self._action(
            file_menu,
            self.tr("Show selections folder"),
            self.show_selections_folder,
            icon="folder-open",
        )
        file_menu.addSeparator()
        self.settings_action = self._action(
            file_menu,
            self.tr("Settings…"),
            self.open_settings,
            QKeySequence.StandardKey.Preferences,
            QAction.MenuRole.PreferencesRole,
            "settings",
        )
        file_menu.addSeparator()
        self._action(
            file_menu,
            self.tr("Quit"),
            self.close,
            QKeySequence.StandardKey.Quit,
            QAction.MenuRole.QuitRole,
        )

        self.help_menu = bar.addMenu(self.tr("&Help"))
        self._action(
            self.help_menu,
            self.tr("User guide"),
            lambda: open_url(about.GUIDE_URL),
            QKeySequence.StandardKey.HelpContents,
            icon="book-open",
        )
        self._action(
            self.help_menu,
            self.tr("Release notes"),
            lambda: open_url(about.RELEASES_URL),
            icon="external-link",
        )
        self._action(
            self.help_menu,
            self.tr("Report a problem…"),
            lambda: open_url(about.bug_report_url()),
            icon="bug",
        )
        self.help_menu.addSeparator()
        self.about_action = self._action(
            self.help_menu,
            self.tr("About %1").replace("%1", APP_NAME),
            self.show_about,
            role=QAction.MenuRole.AboutRole,
            icon="info",
        )

    def new_selection(self) -> None:
        if self.session is not None:
            self.show_start()
        self.start_screen.new_selection()

    def show_selections_folder(self) -> None:
        folder = self.settings.base_dir
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def open_settings(self) -> None:
        if self.session is not None:
            self.session.open_settings()
        else:
            self.start_screen.open_settings()

    def show_about(self) -> None:
        AboutDialog(self).exec()

    # Screens -----------------------------------------------------------------------------

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
        self.settings.window_geometry = self.saveGeometry()
        super().closeEvent(event)
