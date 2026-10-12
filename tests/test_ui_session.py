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
    session.next_button.click()
    assert exported(session) == ["Foto - a2.jpg"]
    assert session.index == 1
    assert "<b>1</b>" in session.total_label.text()
    assert "~" in session.total_label.text() and "0,35" in session.total_label.text().replace(
        ".", ","
    )
    session.next_button.click()  # nothing picked in the last group
    assert session.pages.currentWidget() is session.end_page
    assert "Photos to print: <b>1</b>" in session.end_label.text()
    session.previous_group()
    assert session.index == 1 and session.pages.currentWidget() is session.groups_page


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
    session.next_button.click()
    assert exported(session) == ["Foto - a1.jpg", "Foto - a2.jpg"]
    assert session.previous_button.isEnabled()

    session.previous_button.click()
    assert session.index == 0
    assert session.group_view.picked() == {"a1.jpg", "a2.jpg"}  # previous choice restored
    pick(session, 0)
    session.next_button.click()
    assert exported(session) == ["Foto - a1.jpg"]
    assert session.index == 1


def test_reopen_resumes_where_left(qtbot, tmp_path, photos):
    other = tmp_path / "Other"
    make_photo(other / "z.jpg", pattern=5)
    Selection.create(tmp_path, "R").close()
    first = SessionScreen(tmp_path / "R")
    qtbot.addWidget(first)
    first.add_source(other)
    wait_groups(qtbot, first)
    first.add_source(photos)
    wait_groups(qtbot, first)
    first.next_button.click()  # first group of "Foto" reviewed
    first.close_selection()

    again = SessionScreen(tmp_path / "R")
    qtbot.addWidget(again)
    wait_groups(qtbot, again)
    assert again.source.name == "Foto"  # last used source
    assert again.index == 1
    again.close_selection()


def test_keyboard_flow(qtbot, session, photos):
    from PySide6.QtCore import Qt

    session.add_source(photos)
    wait_groups(qtbot, session)
    view = session.group_view
    session.show()  # Tab reaches a hidden view only as focus change
    qtbot.waitExposed(session)
    qtbot.keyClick(view, Qt.Key.Key_Tab)
    assert view.picked() == set()  # moving does not pick
    assert view.currentIndex().row() == 1
    qtbot.keyClick(view, Qt.Key.Key_Space)
    assert view.picked() == {"a2.jpg"}
    qtbot.keyClick(view, Qt.Key.Key_1)
    assert view.picked() == {"a1.jpg", "a2.jpg"}
    qtbot.keyClick(view, Qt.Key.Key_Space)  # current is a1 again: unpick
    assert view.picked() == {"a2.jpg"}
    qtbot.keyClick(view, Qt.Key.Key_Right)
    assert session.index == 1
    assert exported(session) == ["Foto - a2.jpg"]
    qtbot.keyClick(session.group_view, Qt.Key.Key_Left)
    assert session.index == 0
    assert session.group_view.picked() == {"a2.jpg"}
    qtbot.keyClick(session.group_view, Qt.Key.Key_Return)
    assert session.index == 1
    qtbot.keyClick(session.group_view, Qt.Key.Key_Backspace)
    assert session.index == 0


def test_going_back_keeps_picks(qtbot, session, photos):
    from PySide6.QtCore import Qt

    session.add_source(photos)
    wait_groups(qtbot, session)
    qtbot.keyClick(session.group_view, Qt.Key.Key_Right)
    qtbot.keyClick(session.group_view, Qt.Key.Key_1)  # pick b.jpg, then go back
    qtbot.keyClick(session.group_view, Qt.Key.Key_Left)
    assert session.index == 0
    assert exported(session) == ["Foto - b.jpg"]
    qtbot.keyClick(session.group_view, Qt.Key.Key_Left)  # first group: nothing happens
    assert session.index == 0
    qtbot.keyClick(session.group_view, Qt.Key.Key_Right)
    assert session.group_view.picked() == {"b.jpg"}


def test_threshold_slider_regroups_and_keeps_position(qtbot, session, photos):
    session.add_source(photos)
    wait_groups(qtbot, session)
    # Hashes with known distances: a1-a2 = 3 bits, b far away.
    session.items = [(p, h) for (p, _), h in zip(session.items, [0, 0b111, 2**64 - 1], strict=True)]
    session.regroup()
    assert len(session.groups) == 2
    session.next_button.click()  # now on group with b.jpg
    session.threshold_slider.setValue(0)
    qtbot.waitUntil(lambda: session.selection.threshold == 0, timeout=2000)
    assert len(session.groups) == 3
    assert session.groups[session.index].photos[0].rel_path == "b.jpg"


def test_crop_preview_toggle_in_grid(qtbot, session, photos):
    from PySide6.QtCore import Qt

    session.add_source(photos)
    wait_groups(qtbot, session)
    qtbot.keyClick(session.group_view, Qt.Key.Key_C)
    assert session.group_view.show_crop
    session.group_view.grab()


def test_relink_moved_source(qtbot, session, photos, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    session.add_source(photos)
    wait_groups(qtbot, session)
    session.next_button.click()
    moved = tmp_path / "F" / "Foto"
    moved.parent.mkdir()
    photos.rename(moved)
    session._source_changed()
    assert session.pages.currentWidget() is session.message_page
    assert not session.relink_button.isHidden()

    # A folder without the known photos needs confirmation.
    wrong = tmp_path / "wrong"
    wrong.mkdir()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    assert not session.relink(wrong)

    assert session.relink(moved)
    wait_groups(qtbot, session)
    assert session.index == 1  # progress kept
    assert session.source.path == moved.resolve()


def test_drive_unplugged_while_confirming(qtbot, session, photos, tmp_path):
    session.add_source(photos)
    wait_groups(qtbot, session)
    pick(session, 0)
    photos.rename(tmp_path / "unplugged")
    session.next_button.click()
    assert session.pages.currentWidget() is session.message_page
    assert not session.relink_button.isHidden()


def test_unreadable_photo_is_shown_alone(qtbot, session, photos):
    (photos / "broken.jpg").write_bytes(b"not a photo")
    session.add_source(photos)
    wait_groups(qtbot, session)
    names = [[p.name for p in g.photos] for g in session.groups]
    assert ["broken.jpg"] in names


def test_click_toggles_and_double_click_previews(qtbot, session, photos):
    from PySide6.QtCore import Qt

    session.add_source(photos)
    wait_groups(qtbot, session)
    view = session.group_view
    session.resize(900, 700)
    session.show()
    qtbot.waitExposed(session)
    centers = [view.visualRect(view.photo_model.index(r)).center() for r in (0, 1)]
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=centers[0])
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=centers[1])
    assert view.picked() == {"a1.jpg", "a2.jpg"}  # no Ctrl/Cmd needed
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=centers[0])
    assert view.picked() == {"a2.jpg"}

    previews = []
    view.preview_requested.disconnect(session.open_preview)  # no modal viewer in tests
    view.preview_requested.connect(previews.append)
    # A real double-click is a click followed by a double-click event.
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=centers[1])
    qtbot.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton, pos=centers[1])
    assert previews == [1]
    assert view.picked() == {"a2.jpg"}  # the double-click itself does not change the choice
    view.grab()  # paints the checkboxes
