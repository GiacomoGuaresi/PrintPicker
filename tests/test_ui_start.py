import datetime as dt

import pytest
from PySide6.QtCore import QSettings

from printpicker.selection import Selection, is_selection
from printpicker.ui.main_window import MainWindow
from printpicker.ui.selection_cards import (
    COVER_ROLE,
    DETAILS_ROLE,
    SelectionCardModel,
    cover_tiles,
    days_ago,
)
from printpicker.ui.settings import AppSettings
from printpicker.ui.start_screen import StartScreen

from helpers import make_photo


@pytest.fixture
def settings(tmp_path):
    s = AppSettings(QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))
    s.base_dir = tmp_path / "PrintPicker"
    return s


@pytest.fixture
def screen_for(qtbot, settings):
    def make():
        screen = StartScreen(settings)
        qtbot.addWidget(screen)
        return screen

    return make


def test_lists_existing_selections(settings, screen_for):
    settings.base_dir.mkdir()
    for name in ["A", "B"]:
        Selection.create(settings.base_dir, name).close()
    screen = screen_for()
    assert screen.selection_count() == 2
    assert screen.cards.model().rowCount() == 3  # "New selection" + 2
    assert screen.selected_path() is not None
    assert screen.welcome.isHidden()


def test_empty_state(screen_for):
    screen = screen_for()
    assert screen.selection_count() == 0
    assert not screen.welcome.isHidden()
    assert screen.selected_path() is None


def test_card_shows_photos_cost_and_cover(qtbot, tmp_path, settings, screen_for):
    src = tmp_path / "Foto"
    for i in range(3):
        make_photo(src / f"{i}.jpg", pattern=i)
    with Selection.create(settings.base_dir, "S") as sel:
        source = sel.add_source(src)
        for i in range(3):
            sel.export(source, f"{i}.jpg")
    screen = screen_for()
    model = screen.cards.model()
    index = model.index(1)
    details = model.data(index, DETAILS_ROLE)
    assert details.startswith("3 photo")
    assert "1.05" in details or "1,05" in details  # 3 × 0.35
    model.data(index, COVER_ROLE)
    qtbot.waitUntil(lambda: all(model.data(index, COVER_ROLE)), timeout=5000)
    assert len(model.data(index, COVER_ROLE)) == 3
    screen.cards.grab()  # paints without errors
    screen.shutdown()


def test_create_selection_creates_base_dir(screen_for, settings):
    screen = screen_for()
    path = screen.create_selection("Stampa Natale")
    assert path == settings.base_dir / "Stampa Natale"
    assert is_selection(path)


def test_opening_switches_screen(qtbot, settings):
    settings.base_dir.mkdir()
    Selection.create(settings.base_dir, "A").close()
    window = MainWindow(settings)
    qtbot.addWidget(window)
    cards = window.start_screen.cards
    with qtbot.waitSignal(window.start_screen.selection_opened):
        cards.open_requested.emit(cards.model().index(1))
    assert window.current_selection == settings.base_dir / "A"
    assert window.stack.currentWidget() is not window.start_screen


def test_new_card_starts_new_selection(screen_for, monkeypatch):
    screen = screen_for()
    calls = []
    monkeypatch.setattr(screen, "new_selection", lambda: calls.append(True))
    screen.cards.open_requested.emit(screen.cards.model().index(0))
    assert calls == [True]


@pytest.mark.parametrize(("answer", "deleted"), [("Yes", True), ("Cancel", False)])
def test_delete_selection(settings, screen_for, monkeypatch, answer, deleted):
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
    screen = screen_for()
    screen.delete_selection()
    assert (trashed == [settings.base_dir / "Old"]) is deleted
    assert screen.selection_count() == (0 if deleted else 1)


def test_updated_text(qtbot):
    from printpicker.ui.thumbnails import ThumbnailLoader

    model = SelectionCardModel(ThumbnailLoader())
    today = dt.date(2026, 10, 12)

    def ts(days):
        return dt.datetime.combine(today - dt.timedelta(days=days), dt.time(12)).timestamp()

    assert days_ago(ts(3), today) == 3
    assert model.updated_text(ts(0), today) == "Updated today"
    assert model.updated_text(ts(1), today) == "Updated yesterday"
    assert model.updated_text(ts(3), today) == "Updated 3 day(s) ago"
    assert model.updated_text(ts(30), today).startswith("Updated on ")
    assert model.updated_text(0, today) == ""


@pytest.mark.parametrize("count", [0, 1, 2, 3, 4])
def test_cover_tiles_stay_inside(count):
    from PySide6.QtCore import QRect

    rect = QRect(10, 20, 240, 160)
    tiles = cover_tiles(rect, count)
    assert len(tiles) == count
    assert all(rect.contains(t) for t in tiles)


@pytest.mark.parametrize(
    ("answer", "expected"), [("Nuovo", "Nuovo"), ("Other", "A"), ("a/b", "A"), (None, "A")]
)
def test_rename_selection(settings, screen_for, monkeypatch, answer, expected):
    from PySide6.QtWidgets import QInputDialog, QMessageBox

    settings.base_dir.mkdir()
    for name in ["Other", "A"]:
        Selection.create(settings.base_dir, name).close()
    screen = screen_for()
    screen.cards.setCurrentIndex(
        screen.cards.model().index(2 if screen.selected_path().name == "Other" else 1)
    )
    assert screen.selected_path().name == "A"
    answers = iter([(answer, True), (None, False)] if answer else [(None, False)])
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: next(answers))
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: warnings.append(a))
    screen.rename_selection()
    assert (settings.base_dir / expected).is_dir()
    assert bool(warnings) is (answer in ("Other", "a/b"))
    if expected == "Nuovo":
        assert screen.selected_path() == settings.base_dir / "Nuovo"


def test_keys_and_menu(qtbot, settings, screen_for, monkeypatch):
    from PySide6.QtCore import QPoint, Qt

    settings.base_dir.mkdir()
    Selection.create(settings.base_dir, "A").close()
    screen = screen_for()
    calls = []
    monkeypatch.setattr(screen, "rename_selection", lambda: calls.append("rename"))
    monkeypatch.setattr(screen, "delete_selection", lambda: calls.append("delete"))
    screen.cards.rename_requested.disconnect()
    screen.cards.delete_requested.disconnect()
    screen.cards.rename_requested.connect(lambda _i: screen.rename_selection())
    screen.cards.delete_requested.connect(lambda _i: screen.delete_selection())
    qtbot.keyClick(screen.cards, Qt.Key.Key_F2)
    qtbot.keyClick(screen.cards, Qt.Key.Key_Delete)
    assert calls == ["rename", "delete"]
    labels = [a.text() for a in screen.menu_actions().actions() if not a.isSeparator()]
    assert labels == ["Open", "Open folder", "Rename…", "Delete…"]

    monkeypatch.setattr(screen, "show_menu", lambda *a: calls.append("menu"))
    screen.cards.menu_requested.disconnect()
    screen.cards.menu_requested.connect(lambda *a: screen.show_menu(*a))
    screen.resize(1000, 700)
    screen.show()
    index = screen.cards.model().index(1)
    with qtbot.waitSignal(screen.cards.menu_requested):
        qtbot.mouseClick(
            screen.cards.viewport(),
            Qt.MouseButton.LeftButton,
            pos=screen.cards.menu_button_rect(index).center(),
        )
    assert calls[-1] == "menu"
    with qtbot.waitSignal(screen.selection_opened):
        qtbot.mouseClick(
            screen.cards.viewport(),
            Qt.MouseButton.LeftButton,
            pos=screen.cards.visualRect(index).center() + QPoint(0, 20),
        )
