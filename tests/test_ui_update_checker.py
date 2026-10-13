import json
from datetime import datetime, timedelta

import pytest
from PySide6.QtWidgets import QMessageBox

from printpicker import about
from printpicker.ui import main_window as main_window_module
from printpicker.ui.main_window import MainWindow
from printpicker.ui.update_checker import UpdateChecker, UpdateDialog


class FakeFetcher:
    def __init__(self, body=None, error="", status=None):
        self.body, self.error, self.urls = body, error, []
        self.status = status if status is not None else (200 if body is not None else 0)

    def get(self, url, callback):
        self.urls.append(url)
        callback(self.status, self.body, self.error)


def release(tag="v9.0.0"):
    return json.dumps(
        {
            "tag_name": tag,
            "html_url": f"{about.RELEASES_URL}/tag/{tag}",
            "body": "- new things",
            "draft": False,
            "prerelease": False,
        }
    ).encode()


def run(qtbot, fetcher, current="1.0.0"):
    checker = UpdateChecker(fetcher, current_version=current)
    events = []
    checker.update_available.connect(lambda r: events.append(("new", r.version)))
    checker.up_to_date.connect(lambda: events.append(("ok",)))
    checker.failed.connect(lambda e: events.append(("failed", e)))
    checker.check()
    return events


def test_newer_release_is_reported(qtbot):
    fetcher = FakeFetcher(release("v9.0.0"))
    assert run(qtbot, fetcher) == [("new", "9.0.0")]
    assert fetcher.urls == [about.LATEST_RELEASE_API]


def test_same_version_is_up_to_date(qtbot):
    assert run(qtbot, FakeFetcher(release("v1.0.0"))) == [("ok",)]


def test_no_release_yet_is_up_to_date(qtbot):
    assert run(qtbot, FakeFetcher(None, "Not Found", status=404)) == [("ok",)]


@pytest.mark.parametrize(
    "fetcher",
    [FakeFetcher(None, "offline"), FakeFetcher(b"<html>"), FakeFetcher(None, "boom", status=500)],
)
def test_errors_are_reported(qtbot, fetcher):
    assert run(qtbot, fetcher)[0][0] == "failed"


@pytest.fixture
def window(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)
    shown = {"dialogs": [], "infos": [], "warnings": [], "opened": []}
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: shown["infos"].append(a[2]))
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: shown["warnings"].append(a[2]))
    monkeypatch.setattr(main_window_module, "open_url", shown["opened"].append)
    window.shown = shown
    window.monkeypatch = monkeypatch
    return window


def use(window, fetcher, answer=UpdateDialog.LATER):
    window.update_checker = UpdateChecker(fetcher, parent=window)
    window.update_checker.update_available.connect(window._update_available)
    window.update_checker.up_to_date.connect(window._up_to_date)
    window.update_checker.failed.connect(window._update_failed)

    def fake_exec(dialog):
        window.shown["dialogs"].append(dialog.release.version)
        return answer

    window.monkeypatch.setattr(UpdateDialog, "exec", fake_exec)


def test_download_opens_the_release_page(window):
    use(window, FakeFetcher(release("v9.0.0")), UpdateDialog.DOWNLOAD)
    window.check_for_updates(manual=False)
    assert window.shown["dialogs"] == ["9.0.0"]
    assert window.shown["opened"] == [f"{about.RELEASES_URL}/tag/v9.0.0"]
    assert window.settings.last_update_check is not None


def test_skipped_version_is_not_offered_again_automatically(window):
    use(window, FakeFetcher(release("v9.0.0")), UpdateDialog.SKIP)
    window.check_for_updates(manual=False)
    assert window.settings.skipped_version == "9.0.0"
    window.check_for_updates(manual=False)
    assert window.shown["dialogs"] == ["9.0.0"]
    window.check_for_updates(manual=True)
    assert window.shown["dialogs"] == ["9.0.0", "9.0.0"]


def test_automatic_check_is_silent_when_nothing_new_or_offline(window):
    use(window, FakeFetcher(release(f"v{about.__version__}")))
    window.check_for_updates(manual=False)
    use(window, FakeFetcher(None, "offline"))
    window.check_for_updates(manual=False)
    assert window.shown["infos"] == [] and window.shown["warnings"] == []


def test_manual_check_always_answers(window):
    use(window, FakeFetcher(release(f"v{about.__version__}")))
    window.check_for_updates(manual=True)
    assert about.__version__ in window.shown["infos"][0]
    use(window, FakeFetcher(None, "offline"))
    window.check_for_updates(manual=True)
    assert "offline" in window.shown["warnings"][0]


def test_auto_check_is_scheduled_once_a_day(window, monkeypatch):
    scheduled = []
    monkeypatch.setattr(
        main_window_module.QTimer, "singleShot", lambda ms, fn: scheduled.append(ms)
    )
    window.schedule_update_check()
    assert len(scheduled) == 1
    window.settings.last_update_check = datetime.now() - timedelta(hours=1)
    window.schedule_update_check()
    assert len(scheduled) == 1
    window.settings.auto_update_check = False
    window.settings.last_update_check = datetime.now() - timedelta(days=2)
    window.schedule_update_check()
    assert len(scheduled) == 1
