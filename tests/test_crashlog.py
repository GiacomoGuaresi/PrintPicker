import sys
import threading

import pytest
from PySide6.QtCore import qInstallMessageHandler, qWarning

from printpicker import crashlog


@pytest.fixture
def log(tmp_path, monkeypatch):
    """Install the crash log in tmp_path; every hook it replaces is put back afterwards."""
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    monkeypatch.setattr(threading, "excepthook", threading.excepthook)
    monkeypatch.setattr(sys, "stderr", sys.stderr)
    monkeypatch.setattr(sys, "stdout", sys.stdout)
    enabled = []
    monkeypatch.setattr(crashlog.faulthandler, "enable", lambda f, **kw: enabled.append(f))
    path = crashlog.install(tmp_path / "logs" / crashlog.LOG_NAME)
    yield path, enabled
    qInstallMessageHandler(None)
    crashlog._log.close()
    monkeypatch.setattr(crashlog, "_log", None)


def test_log_starts_with_version_and_enables_faulthandler(log):
    path, enabled = log
    assert f"PrintPicker {crashlog.__version__} started" in path.read_text(encoding="utf-8")
    assert enabled == [crashlog._log]


def test_unhandled_exceptions_are_logged(log):
    path, _ = log
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        sys.excepthook(*sys.exc_info())

    def fail():
        raise ValueError("thread boom")

    thread = threading.Thread(target=fail, name="worker")
    thread.start()
    thread.join()

    text = path.read_text(encoding="utf-8")
    assert "RuntimeError: boom" in text
    assert "Unhandled exception in thread worker" in text
    assert "ValueError: thread boom" in text


def test_qt_warnings_are_logged(log):
    path, _ = log
    qWarning("something odd")
    assert "Qt warning: something odd" in path.read_text(encoding="utf-8")


def test_windowed_build_gets_a_stderr(tmp_path, monkeypatch, log):
    path, _ = log
    crashlog._log.close()
    monkeypatch.setattr(sys, "stderr", None)
    monkeypatch.setattr(sys, "stdout", None)
    crashlog.install(tmp_path / "windowed.log")
    assert sys.stderr is crashlog._log
    assert sys.stdout is not None


def test_unwritable_location_runs_without_log(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("not a folder")
    assert crashlog.install(blocker / crashlog.LOG_NAME) is None


def test_log_dir_is_per_user():
    assert crashlog.log_dir().name == "PrintPicker"
