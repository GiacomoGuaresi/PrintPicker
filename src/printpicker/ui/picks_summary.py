"""Summary of the photos picked per source and folder, with a button to review each."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from printpicker.selection.choices import SourcePicks
from printpicker.ui import theme

# (source id, folder): folder None stands for the whole source.
RowKey = tuple[int, str | None]


class PicksSummary(QFrame):
    """Rows "source → n photos", indented rows per folder when the source has sub-folders,
    and the totals for print at the bottom."""

    review_requested = Signal(int, object)  # source id, folder (None: whole source)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("picksSummary")
        self.setFixedWidth(560)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("picksRows")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setMaximumHeight(300)
        self.total_label = QLabel()
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        layout.addWidget(self.scroll)
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        layout.addWidget(self.total_label)
        self.counts: dict[RowKey, int] = {}
        self.review_buttons: dict[RowKey, QPushButton] = {}

    def set_picks(
        self, picks: list[SourcePicks], total_text: str, current: RowKey | None = None
    ) -> None:
        """Rebuild the rows; ``current`` (the folder or source just finished) is highlighted."""
        self.counts.clear()
        self.review_buttons.clear()
        rows = QWidget()
        rows.setObjectName("picksRows")
        grid = QGridLayout(rows)
        grid.setContentsMargins(0, 0, 4, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(0, 1)
        row = 0
        for item in picks:
            source = item.source
            nested = any(folder for folder, _ in item.folders)
            entries: list[tuple[RowKey, str, int]] = [((source.id, None), source.name, item.total)]
            if nested:
                entries += [
                    ((source.id, folder), "    " + (folder or source.name), count)
                    for folder, count in item.folders
                ]
            for key, name, count in entries:
                is_source = key[1] is None
                label = QLabel(name)
                label.setTextFormat(Qt.TextFormat.PlainText)
                if is_source:
                    font = label.font()
                    font.setBold(True)
                    label.setFont(font)
                count_label = QLabel(self.tr("%n photo(s)", "", count))
                count_label.setAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                if key == current:
                    theme.set_role(label, "current")
                    theme.set_role(count_label, "current")
                elif not is_source:
                    theme.set_role(label, "muted")
                    theme.set_role(count_label, "muted")
                button = theme.set_role(QPushButton(self.tr("Review")), "link")
                button.setToolTip(self.tr("Only the picked photos, to unpick some of them"))
                button.setEnabled(count > 0)
                button.clicked.connect(
                    lambda _checked=False, k=key: self.review_requested.emit(k[0], k[1])
                )
                grid.addWidget(label, row, 0)
                grid.addWidget(count_label, row, 1)
                grid.addWidget(button, row, 2)
                self.counts[key] = count
                self.review_buttons[key] = button
                row += 1
        if not picks:
            grid.addWidget(theme.set_role(QLabel(self.tr("No photos yet")), "muted"), 0, 0)
        self.scroll.setWidget(rows)
        self.total_label.setText(total_text)
