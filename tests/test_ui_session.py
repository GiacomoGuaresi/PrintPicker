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
