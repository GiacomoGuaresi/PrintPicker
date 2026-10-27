import json
import socket
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from PySide6.QtWidgets import QMessageBox

from printpicker import about
from printpicker.ui import main_window as main_window_module
from printpicker.ui.main_window import MainWindow
from printpicker.ui.update_checker import UpdateChecker, UpdateDialog, UrllibFetcher, ssl_context


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


# Real requests against a local HTTP server -------------------------------------------------


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/release":
            body = release("v9.0.0")
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def fetch(qtbot, url):
    replies = []
    fetcher = UrllibFetcher()
    fetcher.get(url, lambda *reply: replies.append((*reply, threading.current_thread())))
    qtbot.waitUntil(lambda: bool(replies), timeout=15_000)
    return replies[0]


def test_fetch_delivers_the_reply_in_the_gui_thread(qtbot, server):
    status, body, error, thread = fetch(qtbot, f"{server}/release")
    assert (status, error) == (200, "")
    assert json.loads(body)["tag_name"] == "v9.0.0"
    assert thread is threading.main_thread()


def test_fetch_reports_http_errors(qtbot, server):
    status, body, error, _ = fetch(qtbot, f"{server}/missing")
    assert (status, body) == (404, None)
    assert error


def test_fetch_reports_unreachable_server(qtbot):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]  # free port, nothing listening once closed
    status, body, error, _ = fetch(qtbot, f"http://127.0.0.1:{port}/")
    assert (status, body) == (0, None)
    assert error


def test_tls_context_has_certificates():
    assert ssl_context().cert_store_stats()["x509_ca"] > 0
