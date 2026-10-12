import pytest

from printpicker.selection import Selection
from printpicker.ui.session_screen import SessionScreen

from helpers import make_photo


@pytest.fixture
def session(qtbot, tmp_path):
    Selection.create(tmp_path, "S").close()
    screen = SessionScreen(tmp_path / "S")
    qtbot.addWidget(screen)
    yield screen
    screen.close_selection()


@pytest.fixture
def photos(tmp_path):
    src = tmp_path / "Foto"
    make_photo(src / "a1.jpg", pattern=1)
    make_photo(src / "a2.jpg", pattern=1, color=(0, 0, 0))
    make_photo(src / "b.jpg", pattern=2)
    return src


def test_empty_selection_asks_for_source(session):
    assert session.pages.currentWidget() is session.empty_page
    assert not session.source_combo.isEnabled()


def test_add_source_analyses_and_groups(qtbot, session, photos):
    session.add_source(photos)
    qtbot.waitUntil(lambda: session.pages.currentWidget() is session.groups_page, timeout=10000)
    assert [len(g.photos) for g in session.groups] == [2, 1]
    assert session.source_combo.count() == 1
    # Adding the same folder again just selects it.
    session.add_source(photos)
    assert session.source_combo.count() == 1


def test_missing_source(qtbot, session, photos, tmp_path):
    session.add_source(photos)
    qtbot.waitUntil(lambda: session.thread is None, timeout=10000)
    photos.rename(tmp_path / "elsewhere")
    session._source_changed()
    assert session.pages.currentWidget() is session.message_page


def test_cancel_shows_message_and_retry_resumes(qtbot, session, photos):
    session.add_source(photos)
    session._cancel_clicked()
    assert session.thread is None
    assert session.pages.currentWidget() is session.message_page
    session.retry_button.click()
    qtbot.waitUntil(lambda: session.pages.currentWidget() is session.groups_page, timeout=10000)


def wait_groups(qtbot, session):
    qtbot.waitUntil(lambda: session.pages.currentWidget() is session.groups_page, timeout=10000)


def pick(session, *rows):
    from PySide6.QtCore import QItemSelectionModel

    sm = session.group_view.selectionModel()
    sm.clearSelection()
    for row in rows:
        sm.select(
            session.group_view.photo_model.index(row), QItemSelectionModel.SelectionFlag.Select
        )


def exported(session):
    return sorted(p.name for p in session.selection.folder.iterdir() if not p.name.startswith("."))


def test_confirm_copies_and_advances(qtbot, session, photos):
    session.add_source(photos)
    wait_groups(qtbot, session)
    assert session.index == 0
    assert len(session.group_view.photo_model.photos) == 2
    pick(session, 1)
    assert session.group_view.picked() == {"a2.jpg"}
    session.confirm_button.click()
    assert exported(session) == ["Foto - a2.jpg"]
    assert session.index == 1
    assert "1" in session.total_label.text()
    session.confirm_button.click()  # nothing picked in the last group
    assert session.pages.currentWidget() is session.message_page


def test_best_cell_size():
    from printpicker.ui.group_view import MIN_CELL, best_cell_size

    assert best_cell_size(1, 1000, 600) == 600
    assert best_cell_size(3, 1200, 700) == 400
    assert best_cell_size(4, 800, 800) == 400
    assert best_cell_size(500, 800, 600) == MIN_CELL


def test_go_back_and_change_choice(qtbot, session, photos):
    session.add_source(photos)
    wait_groups(qtbot, session)
    assert not session.previous_button.isEnabled()
    pick(session, 0, 1)
    session.confirm_button.click()
    assert exported(session) == ["Foto - a1.jpg", "Foto - a2.jpg"]
    assert session.previous_button.isEnabled()

    session.previous_button.click()
    assert session.index == 0
    assert session.group_view.picked() == {"a1.jpg", "a2.jpg"}  # previous choice restored
    pick(session, 0)
    session.confirm_button.click()
    assert exported(session) == ["Foto - a1.jpg"]
    assert session.index == 1
