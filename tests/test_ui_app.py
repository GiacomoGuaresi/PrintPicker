from printpicker.about import APP_NAME
from printpicker.ui.main_window import MainWindow


def test_main_window_opens(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.windowTitle() == APP_NAME


def test_window_geometry_is_remembered(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.close()
    saved = window.settings.window_geometry
    assert not saved.isEmpty()
    again = MainWindow()
    qtbot.addWidget(again)
    assert again.restoreGeometry(again.settings.window_geometry)
