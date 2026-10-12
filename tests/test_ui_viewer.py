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
