from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from printpicker.core.scanner import PhotoFile
from printpicker.ui.viewer import PhotoViewer

from helpers import make_photo


def make_viewer(qtbot, tmp_path, picked=()):
    photos = [PhotoFile("a.jpg"), PhotoFile("b.jpg")]
    for i, p in enumerate(photos):
        make_photo(tmp_path / p.rel_path, size=(900, 600), pattern=i)
    thumb = QImage(90, 60, QImage.Format.Format_RGB888)
    viewer = PhotoViewer(
        photos,
        lambda p: (tmp_path / p.rel_path, tmp_path / "t.jpg"),
        lambda p: thumb,
        set(picked),
    )
    qtbot.addWidget(viewer)
    viewer.show()
    return viewer


def test_loads_full_image_and_browses(qtbot, tmp_path):
    viewer = make_viewer(qtbot, tmp_path)
    qtbot.waitUntil(lambda: viewer.full_image is not None, timeout=5000)
    assert viewer.full_image.width() == 900
    qtbot.keyClick(viewer, Qt.Key.Key_Right)
    assert viewer.row == 1 and "b.jpg" in viewer.caption.text()
    qtbot.keyClick(viewer, Qt.Key.Key_Right)  # stays on the last photo
    assert viewer.row == 1
    qtbot.keyClick(viewer, Qt.Key.Key_Left)
    assert viewer.row == 0


def test_space_toggles_pick(qtbot, tmp_path):
    viewer = make_viewer(qtbot, tmp_path)
    toggled = []
    viewer.toggled.connect(toggled.append)
    qtbot.keyClick(viewer, Qt.Key.Key_Space)
    assert toggled == [0]
    assert viewer.picked_overlay.isVisible()
    viewer.grab()  # paints the frame and badge without errors
    qtbot.keyClick(viewer, Qt.Key.Key_Right)
    assert not viewer.picked_overlay.isVisible()
    qtbot.keyClick(viewer, Qt.Key.Key_Left)
    assert viewer.picked_overlay.isVisible()
    qtbot.keyClick(viewer, Qt.Key.Key_Space)
    assert not viewer.picked_overlay.isVisible()


def test_picked_overlay_covers_the_view(qtbot, tmp_path):
    viewer = make_viewer(qtbot, tmp_path, picked={"a.jpg"})
    viewer.resize(800, 600)
    qtbot.waitUntil(lambda: viewer.picked_overlay.size() == viewer.view.viewport().size())
    badge = viewer.picked_overlay.badge_rect()
    assert viewer.picked_overlay.rect().contains(badge)
    assert badge.right() > 700 and badge.top() < 40  # top-right corner


def test_escape_closes(qtbot, tmp_path):
    viewer = make_viewer(qtbot, tmp_path)
    with qtbot.waitSignal(viewer.finished, timeout=2000):
        qtbot.keyClick(viewer, Qt.Key.Key_Escape)


def test_zoom_keys(qtbot, tmp_path):
    viewer = make_viewer(qtbot, tmp_path)
    viewer.resize(800, 600)
    qtbot.waitUntil(lambda: viewer.full_image is not None, timeout=5000)
    view = viewer.view
    assert view.fitted
    fit = view.zoom()
    qtbot.keyClick(viewer, Qt.Key.Key_Plus)
    assert not view.fitted and view.zoom() > fit
    qtbot.keyClick(viewer, Qt.Key.Key_1)
    assert abs(view.zoom() - 1.0) < 0.01
    assert "100%" in viewer.caption.text()
    qtbot.keyClick(viewer, Qt.Key.Key_0)
    assert view.fitted
    for _ in range(3):
        qtbot.keyClick(viewer, Qt.Key.Key_Minus)  # cannot go below fit
    assert view.fitted
    qtbot.keyClick(viewer, Qt.Key.Key_Plus)
    qtbot.keyClick(viewer, Qt.Key.Key_Right)  # next photo starts fitted
    assert view.fitted


def test_rotation_is_view_only(qtbot, tmp_path):
    viewer = make_viewer(qtbot, tmp_path)
    viewer.resize(800, 600)
    qtbot.waitUntil(lambda: viewer.full_image is not None, timeout=5000)
    before = (tmp_path / "a.jpg").read_bytes()
    landscape_fit = viewer.view.zoom()
    qtbot.keyClick(viewer, Qt.Key.Key_R)
    assert viewer.view.angle == 90
    assert viewer.view.zoom() < landscape_fit  # a portrait-oriented 900x600 fits smaller
    qtbot.keyClick(viewer, Qt.Key.Key_R, Qt.KeyboardModifier.ShiftModifier)
    assert viewer.view.angle == 0
    qtbot.keyClick(viewer, Qt.Key.Key_R)
    qtbot.keyClick(viewer, Qt.Key.Key_Plus)
    qtbot.keyClick(viewer, Qt.Key.Key_1)
    assert abs(viewer.view.zoom() - 1.0) < 0.01  # zoom is correct while rotated
    qtbot.keyClick(viewer, Qt.Key.Key_Right)
    assert viewer.view.angle == 0
    assert (tmp_path / "a.jpg").read_bytes() == before


def test_crop_toggle_and_warning(qtbot, tmp_path):
    photos = [PhotoFile("phone.jpg")]
    make_photo(tmp_path / "phone.jpg", size=(800, 600), pattern=3)  # 4:3
    viewer = PhotoViewer(
        photos, lambda p: (tmp_path / p.rel_path, tmp_path / "t.jpg"), lambda p: None, set()
    )
    qtbot.addWidget(viewer)
    viewer.show()
    qtbot.waitUntil(lambda: viewer.full_image is not None, timeout=5000)
    assert "cropped" in viewer.caption.text()
    toggles = []
    viewer.crop_toggled.connect(toggles.append)
    qtbot.keyClick(viewer, Qt.Key.Key_C)
    assert viewer.view.show_crop and toggles == [True]
    viewer.grab()  # paints the overlay without errors


def test_preloads_neighbours(qtbot, tmp_path):
    viewer = make_viewer(qtbot, tmp_path)
    qtbot.waitUntil(lambda: 1 in viewer._cache, timeout=5000)  # next photo is preloaded
    qtbot.keyClick(viewer, Qt.Key.Key_Right)
    assert viewer.full_image is not None  # shown at once, no thumbnail step
    assert viewer.view.item.pixmap().width() == 900
    assert set(viewer._cache) <= {0, 1}


def test_double_click_toggles_fit_and_actual_size(qtbot, tmp_path):
    viewer = make_viewer(qtbot, tmp_path)
    viewer.resize(400, 300)
    qtbot.waitUntil(lambda: viewer.full_image is not None, timeout=5000)
    view = viewer.view
    center = view.viewport().rect().center()
    qtbot.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton, pos=center)
    assert not view.fitted and abs(view.zoom() - 1.0) < 0.01
    qtbot.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton, pos=center)
    assert view.fitted


def test_mouse_controls(qtbot, tmp_path):
    viewer = make_viewer(qtbot, tmp_path)
    viewer.resize(800, 600)
    assert not viewer.prev_button.isVisible() and viewer.next_button.isVisible()  # first photo
    qtbot.mouseClick(viewer.next_button, Qt.MouseButton.LeftButton)
    assert viewer.row == 1
    assert viewer.prev_button.isVisible() and not viewer.next_button.isVisible()  # last photo
    toggled = []
    viewer.toggled.connect(toggled.append)
    qtbot.mouseClick(viewer.pick_button, Qt.MouseButton.LeftButton)
    assert toggled == [1] and viewer.pick_button.isChecked()
    assert viewer.picked_overlay.isVisible()
    qtbot.keyClick(viewer, Qt.Key.Key_Space)  # the keyboard still works after a click
    assert toggled == [1, 1] and not viewer.pick_button.isChecked()
    with qtbot.waitSignal(viewer.finished, timeout=2000):
        qtbot.mouseClick(viewer.close_button, Qt.MouseButton.LeftButton)


def test_controls_hide_with_the_cursor(qtbot, tmp_path):
    viewer = make_viewer(qtbot, tmp_path)
    viewport = viewer.view.viewport()
    viewer._hide_controls()
    assert not viewer.close_button.isVisible() and not viewer.next_button.isVisible()
    assert viewport.cursor().shape() == Qt.CursorShape.BlankCursor
    qtbot.mouseMove(viewport, viewport.rect().center())
    qtbot.waitUntil(viewer.close_button.isVisible, timeout=2000)
    assert viewer.next_button.isVisible() and not viewer.prev_button.isVisible()
    assert viewport.cursor().shape() != Qt.CursorShape.BlankCursor
    assert viewer._hide_timer.isActive()
