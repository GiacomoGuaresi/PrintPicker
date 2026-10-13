from urllib.parse import parse_qs, urlsplit

from PySide6.QtGui import QAction, QGuiApplication

from printpicker import about
from printpicker.ui.about_dialog import AboutDialog
from printpicker.ui.main_window import MainWindow


def test_about_dialog_shows_version_and_copies_system_info(qtbot):
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    assert about.__version__ in dialog.version_label.text()
    assert dialog.system_info.toPlainText() == about.build_info()
    dialog.copy_button.click()
    assert QGuiApplication.clipboard().text() == about.build_info()


def test_bug_report_url_prefills_the_form():
    url = urlsplit(about.bug_report_url())
    assert f"{url.scheme}://{url.netloc}{url.path}" == about.NEW_ISSUE_URL
    query = parse_qs(url.query)
    assert query["template"] == ["bug_report.yml"]
    assert about.__version__ in query["environment"][0]


def test_menus_use_native_roles(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.about_action.menuRole() == QAction.MenuRole.AboutRole
    assert window.settings_action.menuRole() == QAction.MenuRole.PreferencesRole
    titles = [a.text() for a in window.menuBar().actions()]
    assert titles == ["&File", "&Help"]


def test_new_selection_action(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)
    calls = []
    monkeypatch.setattr(window.start_screen, "new_selection", lambda: calls.append(1))
    window.new_action.trigger()
    assert calls == [1]
