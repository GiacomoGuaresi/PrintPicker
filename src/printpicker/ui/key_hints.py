"""Row of keyboard hints where every key is drawn as a small keycap chip: [Space] pick · …

The chips (``QLabel#key``) and their labels (``QLabel#action``) are styled by the theme.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

# (keys, what they do), e.g. (["←", "→"], "groups")
Hint = tuple[list[str], str]


class KeyHints(QWidget):
    def __init__(self, hints: list[Hint], parent: QWidget | None = None):
        super().__init__(parent)
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
            layout.addSpacing(2)
            layout.addWidget(label)
