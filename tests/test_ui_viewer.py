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
    assert "picked" in viewer.caption.text()
    qtbot.keyClick(viewer, Qt.Key.Key_Space)
    assert "picked" not in viewer.caption.text()


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
