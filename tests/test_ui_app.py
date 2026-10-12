from printpicker.ui.main_window import APP_NAME, MainWindow


def test_main_window_opens(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.windowTitle() == APP_NAME
