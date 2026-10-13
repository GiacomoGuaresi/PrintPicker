import re
from pathlib import Path

from PySide6.QtGui import QFontDatabase, QPalette
from PySide6.QtWidgets import QPushButton

from printpicker.ui import theme

UI_DIR = Path(theme.__file__).parent


def test_palette_is_dark(qapp):
    theme.apply_theme(qapp)
    palette = qapp.palette()
    window = palette.color(QPalette.ColorRole.Window)
    text = palette.color(QPalette.ColorRole.WindowText)
    assert window.lightness() < 40 < 200 < text.lightness()
    assert palette.color(QPalette.ColorRole.Highlight) == theme.ACCENT


def test_style_sheet_has_no_unresolved_tokens():
    sheet = theme.style_sheet()
    assert "@" not in sheet
    assert theme.ACCENT.name() in sheet


def test_bundled_font_is_used(qapp):
    theme.apply_theme(qapp)
    assert theme.FONT_FAMILY in QFontDatabase.families()
    assert qapp.font().family() == theme.FONT_FAMILY


def test_roles_restyle_widgets(qtbot):
    button = QPushButton("Go")
    qtbot.addWidget(button)
    theme.set_role(button, "primary")
    assert button.property("role") == "primary"


def test_colours_come_from_the_theme():
    """No hard-coded hex colours outside theme.py: every colour is a design token."""
    hex_colour = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    offenders = [
        f"{path.name}: {match}"
        for path in UI_DIR.glob("*.py")
        if path.name != "theme.py"
        for match in hex_colour.findall(path.read_text())
    ]
    assert offenders == []
