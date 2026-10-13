from PySide6.QtWidgets import QApplication

from printpicker.ui.selftest import run_self_test


def test_self_test_passes(qtbot, capsys, model):
    assert run_self_test(QApplication.instance()) == 0
    assert "FAIL" not in capsys.readouterr().out
