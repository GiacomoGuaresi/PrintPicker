"""PrintPicker's look: one dark theme for every platform.

Colours are design tokens taken from the logo (teal for actions and focus, amber for picked
photos). :func:`apply_theme` installs them as Fusion style + palette + one global style
sheet, so widgets pick them up through ``palette()`` and custom painters can import the
tokens directly. Widgets opt into variants with :func:`set_role` (e.g. a primary button).
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QIcon,
    QPainter,
    QPalette,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QWidget

RESOURCES = Path(__file__).resolve().parent.parent / "resources"
FONTS_DIR = RESOURCES / "fonts"
ICONS_DIR = RESOURCES / "icons"
LOGO_PATH = RESOURCES / "logo.svg"
FONT_FAMILY = "Inter"

# Surfaces, from the window background up: neutral greys as in macOS dark mode, not black.
BG = QColor("#2B2B2D")
SURFACE = QColor("#333336")
SURFACE_2 = QColor("#3C3C3F")
SURFACE_3 = QColor("#47474A")
VIEWER_BG = QColor("#1C1C1E")  # full-screen preview: darker, so the photo stands out
BORDER = QColor("#434346")
BORDER_STRONG = QColor("#58585C")

# Text.
TEXT = QColor("#EBEBF0")
TEXT_MUTED = QColor("#A1A1A6")
TEXT_FAINT = QColor("#76767B")

# Accents.
ACCENT = QColor("#22B5AA")  # actions, focus, selection
ACCENT_HOVER = QColor("#35C7BC")
ACCENT_PRESSED = QColor("#1A9A90")
ON_ACCENT = QColor("#071B19")  # text on ACCENT
PICK = QColor("#FFB020")  # a photo chosen for print
ON_PICK = QColor("#2A1C00")
DANGER = QColor("#F0616D")
OVERLAY = QColor(0, 0, 0, 120)  # controls drawn over a photo
OVERLAY_HOVER = QColor(0, 0, 0, 180)

RADIUS = 8
RADIUS_SMALL = 6
RADIUS_LARGE = 12


def css(color: QColor) -> str:
    """``color`` for a style sheet, keeping its alpha."""
    if color.alpha() == 255:
        return color.name()
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"


def set_role(widget: QWidget, role: str) -> QWidget:
    """Give ``widget`` a style variant from the global style sheet (``primary``, ``muted``…)."""
    widget.setProperty("role", role)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    return widget


ICON_SIZES = (16, 20, 24, 32, 48, 64, 96)


def svg_pixmap(svg: bytes, size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(QByteArray(svg)).render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap


@cache
def _icon(name: str, color: str, checked: str | None) -> QIcon:
    source = (ICONS_DIR / f"{name}.svg").read_text(encoding="utf-8")
    result = QIcon()
    variants = [
        (QIcon.Mode.Normal, QIcon.State.Off, color),
        (QIcon.Mode.Disabled, QIcon.State.Off, TEXT_FAINT.name()),
    ]
    if checked:
        variants.append((QIcon.Mode.Normal, QIcon.State.On, checked))
    for mode, state, fill in variants:
        svg = source.replace("currentColor", fill).encode()
        for size in ICON_SIZES:
            result.addPixmap(svg_pixmap(svg, size), mode, state)
    return result


def icon(name: str, color: QColor = TEXT, checked: QColor | None = None) -> QIcon:
    """A Lucide line icon (``resources/icons/<name>.svg``) drawn in ``color``; ``checked``
    is its colour on a checked button."""
    return _icon(name, color.name(), checked.name() if checked else None)


def logo(size: int) -> QPixmap:
    """The app logo at ``size`` × ``size`` logical pixels, sharp on high-DPI screens."""
    app = QGuiApplication.instance()
    ratio = app.devicePixelRatio() if app is not None else 1.0
    pixmap = svg_pixmap(LOGO_PATH.read_bytes(), round(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def palette() -> QPalette:
    p = QPalette()
    roles = QPalette.ColorRole
    for role, color in (
        (roles.Window, BG),
        (roles.WindowText, TEXT),
        (roles.Base, SURFACE),
        (roles.AlternateBase, SURFACE_2),
        (roles.Text, TEXT),
        (roles.PlaceholderText, TEXT_MUTED),
        (roles.Button, SURFACE_2),
        (roles.ButtonText, TEXT),
        (roles.BrightText, QColor("white")),
        (roles.Highlight, ACCENT),
        (roles.HighlightedText, ON_ACCENT),
        (roles.Link, ACCENT),
        (roles.LinkVisited, ACCENT_PRESSED),
        (roles.ToolTipBase, SURFACE_3),
        (roles.ToolTipText, TEXT),
        (roles.Light, SURFACE_3),
        (roles.Midlight, SURFACE_2),
        (roles.Mid, BORDER),
        (roles.Dark, QColor("#0A0B0C")),
        (roles.Shadow, QColor("#000000")),
        (roles.Accent, ACCENT),
    ):
        p.setColor(role, color)
    disabled = QPalette.ColorGroup.Disabled
    for role in (roles.WindowText, roles.Text, roles.ButtonText):
        p.setColor(disabled, role, TEXT_FAINT)
    p.setColor(disabled, roles.Button, SURFACE)
    p.setColor(disabled, roles.Highlight, SURFACE_3)
    return p


STYLE_SHEET = """
QToolTip {
    background: @SURFACE_3; color: @TEXT; border: 1px solid @BORDER_STRONG;
    border-radius: 6px; padding: 4px 8px;
}

QLabel[role="title"] { font-size: 22pt; font-weight: 700; }
QLabel[role="heading"] { font-size: 15pt; font-weight: 600; }
QLabel[role="muted"] { color: @TEXT_MUTED; }
QLabel[role="danger"] { color: @DANGER; }
QLabel[role="current"] { color: @ACCENT; font-weight: 600; }

QFrame#welcome { background: @SURFACE; border: 1px solid @BORDER; border-radius: @RADIUS_LARGEpx; }
QFrame#picksSummary {
    background: @SURFACE; border: 1px solid @BORDER; border-radius: @RADIUS_LARGEpx;
}
#picksRows { background: transparent; }

QFrame#topBar { background: @BG; border-bottom: 1px solid @BORDER; }
QFrame#separator { background: @BORDER; }
QFrame#bottomBar {
    background: @SURFACE; border: 1px solid @BORDER; border-radius: @RADIUS_LARGEpx;
}
QLabel#stateIcon { background: @SURFACE_2; border-radius: 38px; }

/* Keyboard hints (key_hints.py): keycap chips and what they do. */
QLabel#key {
    background: @SURFACE_2; color: @TEXT; border: 1px solid @BORDER_STRONG;
    border-bottom-width: 2px; border-radius: 5px; padding: 0px 5px; font-weight: 600;
}
QLabel#action { color: @TEXT_MUTED; }

QPushButton {
    background: @SURFACE_2; color: @TEXT; border: 1px solid @BORDER;
    border-radius: @RADIUSpx; padding: 6px 14px; min-height: 18px;
}
QPushButton:hover { background: @SURFACE_3; border-color: @BORDER_STRONG; }
QPushButton:pressed { background: @SURFACE; }
QPushButton:focus { border-color: @ACCENT; }
QPushButton:disabled { color: @TEXT_FAINT; background: @SURFACE; border-color: @SURFACE_2; }
QPushButton[role="primary"] {
    background: @ACCENT; color: @ON_ACCENT; border: 1px solid @ACCENT; font-weight: 600;
}
QPushButton[role="primary"]:hover { background: @ACCENT_HOVER; border-color: @ACCENT_HOVER; }
QPushButton[role="primary"]:pressed { background: @ACCENT_PRESSED; }
QPushButton[role="primary"]:focus { border-color: @TEXT; }
QPushButton[role="primary"]:disabled {
    background: @SURFACE_2; color: @TEXT_FAINT; border-color: @SURFACE_2;
}
QPushButton[role="flat"] { background: transparent; border-color: transparent; }
QPushButton[role="flat"]:hover { background: @SURFACE_2; }
QPushButton[role="link"] {
    background: transparent; border: none; color: @ACCENT; padding: 2px 0px; text-align: left;
}
QPushButton[role="link"]:hover { color: @ACCENT_HOVER; text-decoration: underline; }

QToolButton {
    background: transparent; color: @TEXT; border: 1px solid transparent;
    border-radius: @RADIUSpx; padding: 5px;
}
QToolButton:hover { background: @SURFACE_2; }
QToolButton:pressed { background: @SURFACE_3; }
QToolButton:checked { background: @SURFACE_3; color: @ACCENT; }

QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background: @SURFACE_2; color: @TEXT; border: 1px solid @BORDER;
    border-radius: @RADIUSpx; padding: 5px 10px; min-height: 18px;
    selection-background-color: @ACCENT; selection-color: @ON_ACCENT;
}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: @BORDER_STRONG;
}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: @ACCENT;
}
QComboBox:disabled, QLineEdit:disabled { color: @TEXT_FAINT; background: @SURFACE; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: @SURFACE_2; border: 1px solid @BORDER_STRONG; border-radius: 6px;
    padding: 4px; outline: none;
    selection-background-color: @SURFACE_3; selection-color: @TEXT;
}

QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid @BORDER_STRONG; background: @SURFACE_2;
}
QCheckBox::indicator:hover { border-color: @ACCENT; }
QCheckBox::indicator:checked {
    background: @ACCENT; border-color: @ACCENT; image: url(@CHECK_ICON);
}

QSlider::groove:horizontal { height: 4px; background: @SURFACE_3; border-radius: 2px; }
QSlider::sub-page:horizontal { background: @ACCENT; border-radius: 2px; }
QSlider::handle:horizontal {
    background: @TEXT; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px;
}
QSlider::handle:horizontal:hover { background: white; }

QProgressBar {
    background: @SURFACE_2; border: none; border-radius: 4px; min-height: 8px; max-height: 8px;
    color: transparent; text-align: center;
}
QProgressBar::chunk { background: @ACCENT; border-radius: 4px; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle { background: @SURFACE_3; border-radius: 3px; }
QScrollBar::handle:vertical { min-height: 32px; }
QScrollBar::handle:horizontal { min-width: 32px; }
QScrollBar::handle:hover { background: @BORDER_STRONG; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0px; height: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QMenuBar { background: @BG; color: @TEXT; }
QMenuBar::item { padding: 4px 10px; background: transparent; border-radius: 4px; }
QMenuBar::item:selected { background: @SURFACE_2; }
QMenu {
    background: @SURFACE_2; color: @TEXT; border: 1px solid @BORDER_STRONG;
    border-radius: @RADIUSpx; padding: 4px;
}
QMenu::item { padding: 6px 24px 6px 12px; border-radius: 4px; }
QMenu::item:selected { background: @SURFACE_3; }
QMenu::item:disabled { color: @TEXT_FAINT; }
QMenu::separator { height: 1px; background: @BORDER; margin: 4px 8px; }

QTableView, QTableWidget {
    background: @SURFACE; alternate-background-color: @SURFACE_2; color: @TEXT;
    border: 1px solid @BORDER; border-radius: @RADIUSpx; gridline-color: @BORDER;
    selection-background-color: @SURFACE_3; selection-color: @TEXT;
}
QHeaderView::section {
    background: @SURFACE_2; color: @TEXT_MUTED; border: none;
    border-bottom: 1px solid @BORDER; padding: 6px 8px; font-weight: 600;
}
QTableCornerButton::section { background: @SURFACE_2; border: none; }

QGroupBox {
    border: 1px solid @BORDER; border-radius: @RADIUS_LARGEpx;
    margin-top: 14px; padding: 14px 12px 10px 12px;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 12px; padding: 0 4px; color: @TEXT_MUTED;
    font-weight: 600;
}

QDialog { background: @BG; }
QTextBrowser, QPlainTextEdit {
    background: @SURFACE; color: @TEXT; border: 1px solid @BORDER; border-radius: @RADIUSpx;
    padding: 6px;
}
"""


def style_sheet() -> str:
    tokens = {
        name: css(value) if isinstance(value, QColor) else str(value)
        for name, value in globals().items()
        if name.isupper() and isinstance(value, (QColor, int))
    }
    text = STYLE_SHEET.replace("@CHECK_ICON", _check_icon_path())
    # Longest names first, so @SURFACE_2 is not read as @SURFACE + "_2".
    for name in sorted(tokens, key=len, reverse=True):
        text = text.replace(f"@{name}", tokens[name])
    return text


def _check_icon_path() -> str:
    """The check mark of checked checkboxes: style sheets need an image file, so the Lucide
    icon is written once, in the checkbox text colour, to the app's cache folder."""
    from PySide6.QtCore import QStandardPaths

    folder = Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
        or Path.home()
    )
    path = folder / f"check-{ON_ACCENT.name()[1:]}.svg"
    if not path.exists():
        try:
            folder.mkdir(parents=True, exist_ok=True)
            svg = (ICONS_DIR / "check.svg").read_text(encoding="utf-8")
            path.write_text(
                svg.replace("currentColor", ON_ACCENT.name()).replace(
                    'stroke-width="2"', 'stroke-width="3"'
                ),
                encoding="utf-8",
            )
        except OSError:
            return ""
    return path.as_posix()


def load_fonts() -> bool:
    """Register the bundled Inter font; False if it is missing (the system font stays)."""
    loaded = False
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        loaded |= QFontDatabase.addApplicationFont(str(path)) != -1
    return loaded


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    if load_fonts():
        font = QFont(FONT_FAMILY)
        font.setPointSizeF(app.font().pointSizeF())
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        app.setFont(font)
    app.setPalette(palette())
    app.setStyleSheet(style_sheet())
    # Dark title bar and native dialogs where the platform supports it.
    QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)
