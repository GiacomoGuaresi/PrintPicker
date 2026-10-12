import pytest
from PySide6.QtCore import QSettings

from printpicker.selection import Selection, is_selection
from printpicker.ui.main_window import MainWindow
from printpicker.ui.settings import AppSettings
from printpicker.ui.start_screen import StartScreen


@pytest.fixture
def settings(tmp_path):
    s = AppSettings(QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))
    s.base_dir = tmp_path / "PrintPicker"
    return s


def test_lists_existing_selections(qtbot, settings):
    settings.base_dir.mkdir()
    for name in ["A", "B"]:
        Selection.create(settings.base_dir, name).close()
    (settings.base_dir / "A" / "x.jpg").write_bytes(b"")
    screen = StartScreen(settings)
    qtbot.addWidget(screen)
    assert screen.list.count() == 2
    assert screen.open_button.isEnabled()


def test_create_selection_creates_base_dir(qtbot, settings):
    screen = StartScreen(settings)
    qtbot.addWidget(screen)
    path = screen.create_selection("Stampa Natale")
    assert path == settings.base_dir / "Stampa Natale"
    assert is_selection(path)


def test_opening_switches_screen(qtbot, settings):
    settings.base_dir.mkdir()
    Selection.create(settings.base_dir, "A").close()
    window = MainWindow(settings)
    qtbot.addWidget(window)
    with qtbot.waitSignal(window.start_screen.selection_opened):
        window.start_screen.open_button.click()
    assert window.current_selection == settings.base_dir / "A"
    assert window.stack.currentWidget() is not window.start_screen


@pytest.mark.parametrize(("answer", "deleted"), [("Yes", True), ("Cancel", False)])
def test_delete_selection(qtbot, settings, monkeypatch, answer, deleted):
    import shutil

    from PySide6.QtWidgets import QMessageBox

    from printpicker.ui import start_screen

    settings.base_dir.mkdir()
    Selection.create(settings.base_dir, "Old").close()
    trashed = []
    monkeypatch.setattr(
        start_screen, "move_to_trash", lambda p: trashed.append(p) or shutil.rmtree(p) or True
    )
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: getattr(QMessageBox.StandardButton, answer)
    )
    screen = StartScreen(settings)
    qtbot.addWidget(screen)
    screen.delete_selection()
    assert (trashed == [settings.base_dir / "Old"]) is deleted
    assert screen.list.count() == (0 if deleted else 1)
    assert screen.delete_button.isEnabled() is not deleted
