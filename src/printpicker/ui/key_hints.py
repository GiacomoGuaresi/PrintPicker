"""Row of keyboard hints where every key is drawn as a small keycap chip: [Space] pick · …"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

# (keys, what they do), e.g. (["←", "→"], "groups")
Hint = tuple[list[str], str]

LIGHT_STYLE = """
QLabel#key {
    background: palette(button);
    color: palette(button-text);
    border: 1px solid palette(mid);
    border-bottom-width: 2px;
    border-radius: 4px;
    padding: 0px 5px;
    font-weight: 600;
}
"""

DARK_STYLE = """
QLabel#key {
    background: #2c2c2c;
    color: #eee;
    border: 1px solid #555;
    border-bottom-width: 2px;
    border-radius: 4px;
    padding: 0px 5px;
    font-weight: 600;
}
QLabel#action { color: #999; }
"""


class KeyHints(QWidget):
    def __init__(self, hints: list[Hint], dark: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(DARK_STYLE if dark else LIGHT_STYLE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)
        self.chips: list[QLabel] = []
        for i, (keys, action) in enumerate(hints):
            if i:
                layout.addSpacing(14)
            for key in keys:
                chip = QLabel(key)
                chip.setObjectName("key")
                chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
                chip.setMinimumWidth(chip.sizeHint().height())
                self.chips.append(chip)
                layout.addWidget(chip)
            label = QLabel(action)
            label.setObjectName("action")
            if not dark:
                palette = label.palette()
                dim = palette.color(QPalette.ColorRole.PlaceholderText)
                palette.setColor(QPalette.ColorRole.WindowText, dim)
                label.setPalette(palette)
            layout.addSpacing(2)
            layout.addWidget(label)
