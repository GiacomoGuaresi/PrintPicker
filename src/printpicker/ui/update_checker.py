"""Check GitHub for a newer release and offer it (see ``core/updates.py`` for the rules)."""

from __future__ import annotations

import json
import ssl
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Protocol

import certifi
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from printpicker import about
from printpicker.core.updates import ReleaseFormatError, ReleaseInfo, is_newer, parse_release
from printpicker.ui import theme

TIMEOUT_S = 10

# callback(status, body, error): HTTP status (0 without a reply), body (None when the request
# failed) and a short error text.
Callback = Callable[[int, bytes | None, str], None]


class Fetcher(Protocol):
    def get(self, url: str, callback: Callback) -> None: ...


def ssl_context() -> ssl.SSLContext:
    """Python's OpenSSL with certifi's CA bundle: the same certificates on every platform."""
    return ssl.create_default_context(cafile=certifi.where())


def fetch(url: str) -> tuple[int, bytes | None, str]:
    """Blocking HTTP GET; returns the callback's (status, body, error)."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"{about.APP_NAME}/{about.__version__}",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S, context=ssl_context()) as reply:
            return reply.status, reply.read(), ""
    except urllib.error.HTTPError as exc:
        return exc.code, None, str(exc)
    except urllib.error.URLError as exc:
        return 0, None, str(exc.reason)
    except (OSError, ValueError) as exc:  # timeouts, broken connections, bad URLs
        return 0, None, str(exc) or type(exc).__name__


class UrllibFetcher(QObject):
    """HTTP GET with Python's urllib in a background thread; the callback runs in the GUI thread.

    Not QtNetwork: on Windows 11 25H2 its TLS (schannel) crashed the app in Qt's HTTP thread.
    """

    _done = Signal(object, int, object, str)  # callback, status, body, error

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # Emitted from the worker thread, delivered (queued) in this object's thread.
        self._done.connect(self._deliver)

    def get(self, url: str, callback: Callback) -> None:
        def run() -> None:
            self._done.emit(callback, *fetch(url))

        threading.Thread(target=run, name="update-check", daemon=True).start()

    def _deliver(self, callback: Callback, status: int, body: bytes | None, error: str) -> None:
        callback(status, body, error)


class UpdateChecker(QObject):
    """``check()`` emits exactly one of ``update_available``, ``up_to_date`` or ``failed``."""

    update_available = Signal(object)  # ReleaseInfo
    up_to_date = Signal()
    failed = Signal(str)

    def __init__(
        self,
        fetcher: Fetcher | None = None,
        current_version: str = about.__version__,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.fetcher = fetcher or UrllibFetcher(self)
        self.current_version = current_version
        self.busy = False

    def check(self) -> None:
        if self.busy:
            return
        self.busy = True
        self.fetcher.get(about.LATEST_RELEASE_API, self._on_reply)

    def _on_reply(self, status: int, body: bytes | None, error: str) -> None:
        self.busy = False
        if status == 404:  # the repository has no published release yet
            self.up_to_date.emit()
            return
        if body is None:
            self.failed.emit(error)
            return
        try:
            release = parse_release(json.loads(body))
        except (ValueError, ReleaseFormatError) as exc:
            self.failed.emit(str(exc))
            return
        if is_newer(release.version, self.current_version):
            self.update_available.emit(release)
        else:
            self.up_to_date.emit()


class UpdateDialog(QDialog):
    """Offers a release: Download (opens its page), Skip this version, or Later."""

    DOWNLOAD, SKIP, LATER = 1, 2, 0

    def __init__(
        self, release: ReleaseInfo, current: str = about.__version__, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.release = release
        self.setWindowTitle(self.tr("Update available"))
        self.setMinimumWidth(520)

        icon = QLabel()
        icon.setObjectName("stateIcon")
        icon.setFixedSize(56, 56)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("border-radius: 28px;")
        icon.setPixmap(theme.icon("download", theme.ACCENT).pixmap(26))
        title = theme.set_role(
            QLabel(
                self.tr("%1 %2 is available")
                .replace("%1", about.APP_NAME)
                .replace("%2", release.version)
            ),
            "heading",
        )
        subtitle = theme.set_role(
            QLabel(self.tr("You have version %1.").replace("%1", current)), "muted"
        )
        heading = QVBoxLayout()
        heading.setSpacing(2)
        heading.addWidget(title)
        heading.addWidget(subtitle)
        top = QHBoxLayout()
        top.setSpacing(14)
        top.addWidget(icon)
        top.addLayout(heading, 1)

        self.notes = QTextBrowser()
        self.notes.setOpenExternalLinks(True)
        self.notes.setMarkdown(release.notes or self.tr("No release notes."))
        self.notes.setMinimumHeight(200)

        self.skip_button = QPushButton(self.tr("Skip this version"))
        theme.set_role(self.skip_button, "flat")
        self.skip_button.clicked.connect(lambda: self.done(self.SKIP))
        later = QPushButton(self.tr("Later"))
        later.clicked.connect(lambda: self.done(self.LATER))
        self.download_button = QPushButton(
            theme.icon("download", theme.ON_ACCENT), self.tr("Download")
        )
        theme.set_role(self.download_button, "primary")
        self.download_button.setDefault(True)
        self.download_button.clicked.connect(lambda: self.done(self.DOWNLOAD))
        buttons = QHBoxLayout()
        buttons.addWidget(self.skip_button)
        buttons.addStretch()
        buttons.addWidget(later)
        buttons.addWidget(self.download_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 16)
        layout.setSpacing(14)
        layout.addLayout(top)
        layout.addWidget(theme.set_role(QLabel(self.tr("What's new")), "muted"))
        layout.addWidget(self.notes, 1)
        layout.addLayout(buttons)
