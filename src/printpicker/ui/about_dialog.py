"""About PrintPicker: version, links, system details for bug reports, credits."""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from printpicker import about
from printpicker.ui import theme

CREDITS = (
    ("Qt for Python (PySide6)", "https://www.qt.io/qt-for-python", "LGPL-3.0"),
    ("DINOv2", "https://github.com/facebookresearch/dinov2", "Apache-2.0"),
    ("ONNX Runtime", "https://onnxruntime.ai", "MIT"),
    ("Pillow · pillow-heif · rawpy", "https://python-pillow.org", "MIT-CMU · BSD · MIT"),
    ("Lucide icons", "https://lucide.dev", "ISC"),
    ("Inter typeface", "https://rsms.me/inter/", "OFL-1.1"),
)


def open_url(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("About %1").replace("%1", about.APP_NAME))

        logo = QLabel()
        logo.setPixmap(theme.logo(96))
        name = theme.set_role(QLabel(about.APP_NAME), "title")
        self.version_label = theme.set_role(
            QLabel(self.tr("Version %1").replace("%1", about.__version__)), "muted"
        )
        tagline = QLabel(
            self.tr("Pick the best shots from your photo archive and get them ready for print.")
        )
        tagline.setWordWrap(True)
        for label in (logo, name, self.version_label, tagline):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        links = QHBoxLayout()
        links.addStretch()
        for icon, text, url in (
            ("github", self.tr("GitHub"), about.REPO_URL),
            ("bug", self.tr("Report a problem"), about.bug_report_url()),
            ("book-open", self.tr("License"), about.LICENSE_URL),
        ):
            button = QPushButton(theme.icon(icon, theme.ACCENT), text)
            theme.set_role(button, "link")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(url.split("?")[0])
            button.clicked.connect(lambda _=False, u=url: open_url(u))
            links.addWidget(button)
            links.addSpacing(10)
        links.addStretch()

        system_title = theme.set_role(QLabel(self.tr("System information")), "muted")
        self.system_info = QPlainTextEdit(about.build_info())
        self.system_info.setReadOnly(True)
        self.system_info.setFixedHeight(118)
        self.copy_button = QPushButton(theme.icon("copy"), self.tr("Copy"))
        self.copy_button.clicked.connect(self.copy_system_info)
        system_row = QHBoxLayout()
        system_row.addWidget(system_title)
        system_row.addStretch()
        system_row.addWidget(self.copy_button)

        credits = theme.set_role(
            QLabel(
                self.tr("Built with")
                + " "
                + ", ".join(
                    f"<a href='{url}'>{name}</a> ({licence})" for name, url, licence in CREDITS
                )
                + "."
            ),
            "muted",
        )
        credits.setWordWrap(True)
        credits.setOpenExternalLinks(True)
        copyright_label = theme.set_role(
            QLabel(f"{about.COPYRIGHT} · {about.LICENSE_NAME}"), "muted"
        )
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        for label in (tagline, credits):
            label.setFixedWidth(424)  # wrapped labels need a width to compute their height
        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        layout.setContentsMargins(28, 24, 28, 18)
        layout.setSpacing(6)
        layout.addWidget(logo)
        layout.addSpacing(4)
        layout.addWidget(name)
        layout.addWidget(self.version_label)
        layout.addSpacing(6)
        layout.addWidget(tagline)
        layout.addSpacing(4)
        layout.addLayout(links)
        layout.addSpacing(12)
        layout.addLayout(system_row)
        layout.addWidget(self.system_info)
        layout.addSpacing(8)
        layout.addWidget(credits)
        layout.addSpacing(8)
        layout.addWidget(copyright_label)
        layout.addWidget(buttons)

    def copy_system_info(self) -> None:
        QGuiApplication.clipboard().setText(self.system_info.toPlainText())
        self.copy_button.setText(self.tr("Copied"))
        self.copy_button.setIcon(theme.icon("check", theme.ACCENT))
