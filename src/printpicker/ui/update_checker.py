"""Check GitHub for a newer release and offer it (see ``core/updates.py`` for the rules)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Protocol

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
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

TIMEOUT_MS = 10_000

# callback(status, body, error): HTTP status (0 without a reply), body (None when the request
# failed) and a short error text.
Callback = Callable[[int, bytes | None, str], None]


class Fetcher(Protocol):
    def get(self, url: str, callback: Callback) -> None: ...


class NetworkFetcher(QObject):
    """HTTP GET with Qt's network stack (system TLS on every platform)."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.manager = QNetworkAccessManager(self)

    def get(self, url: str, callback: Callback) -> None:
        request = QNetworkRequest(QUrl(url))
        request.setHeader(
            QNetworkRequest.KnownHeaders.UserAgentHeader, f"{about.APP_NAME}/{about.__version__}"
        )
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setTransferTimeout(TIMEOUT_MS)
        reply = self.manager.get(request)

        def finished() -> None:
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) or 0
            if reply.error() == QNetworkReply.NetworkError.NoError:
                callback(status, bytes(reply.readAll().data()), "")
            else:
                callback(status, None, reply.errorString())
            reply.deleteLater()

        reply.finished.connect(finished)


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
        self.fetcher = fetcher or NetworkFetcher(self)
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
