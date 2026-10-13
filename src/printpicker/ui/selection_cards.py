"""Grid of selection cards on the start screen: cover mosaic, name, photos, cost, last change."""

from __future__ import annotations

import datetime as dt

from PySide6.QtCore import (
    QAbstractListModel,
    QLocale,
    QModelIndex,
    QPoint,
    QRect,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QListView, QStyle, QStyledItemDelegate, QStyleOptionViewItem

from printpicker.core.pricing import PriceList
from printpicker.selection import SelectionSummary
from printpicker.ui import theme
from printpicker.ui.money import format_money
from printpicker.ui.thumbnails import ThumbnailLoader

SPACING = 16
MIN_CARD = 200
MAX_CARD = 280
TEXT_HEIGHT = 74
RADIUS = theme.RADIUS_LARGE
MENU_SIZE = 30

SUMMARY_ROLE = Qt.ItemDataRole.UserRole
COVER_ROLE = Qt.ItemDataRole.UserRole + 1
DETAILS_ROLE = Qt.ItemDataRole.UserRole + 2
UPDATED_ROLE = Qt.ItemDataRole.UserRole + 3


def days_ago(timestamp: float, today: dt.date | None = None) -> int:
    """Whole calendar days between a timestamp and today (0 = today)."""
    day = dt.datetime.fromtimestamp(timestamp).date()
    return ((today or dt.date.today()) - day).days


class SelectionCardModel(QAbstractListModel):
    """Row 0 is the "New selection" card; the other rows are the selections."""

    def __init__(self, loader: ThumbnailLoader, parent=None) -> None:
        super().__init__(parent)
        self.loader = loader
        self.summaries: list[SelectionSummary] = []
        self.price_list: PriceList | None = None
        loader.ready.connect(self._thumbnail_ready)

    def set_summaries(self, summaries: list[SelectionSummary], price_list: PriceList) -> None:
        self.beginResetModel()
        self.summaries = list(summaries)
        self.price_list = price_list
        self.endResetModel()

    def summary(self, index: QModelIndex) -> SelectionSummary | None:
        row = index.row()
        return self.summaries[row - 1] if index.isValid() and row > 0 else None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self.summaries) + 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        summary = self.summary(index)
        if summary is None:
            if role == Qt.ItemDataRole.DisplayRole:
                return self.tr("New selection")
            if role == Qt.ItemDataRole.ToolTipRole:
                return self.tr("Create a new print selection")
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return summary.name
        if role == Qt.ItemDataRole.ToolTipRole:
            return str(summary.folder)
        if role == SUMMARY_ROLE:
            return summary
        if role == DETAILS_ROLE:
            return self.details_text(summary)
        if role == UPDATED_ROLE:
            return self.updated_text(summary.last_used)
        if role == COVER_ROLE:
            return [self.loader.request(str(photo), photo, thumb) for photo, thumb in summary.cover]
        return None

    def details_text(self, summary: SelectionSummary) -> str:
        count = summary.photo_count
        if not count:
            return self.tr("No photos yet")
        text = self.tr("%n photo(s)", "", count)
        if self.price_list is not None:
            estimate = self.price_list.estimate(count)
            text += "  ·  ~" + format_money(estimate.total, self.price_list.currency)
        return text

    def updated_text(self, timestamp: float, today: dt.date | None = None) -> str:
        if timestamp <= 0:
            return ""
        days = days_ago(timestamp, today)
        if days <= 0:
            return self.tr("Updated today")
        if days == 1:
            return self.tr("Updated yesterday")
        if days < 7:
            return self.tr("Updated %n day(s) ago", "", days)
        date = dt.datetime.fromtimestamp(timestamp).date()
        formatted = QLocale().toString(date, QLocale.FormatType.ShortFormat)
        return self.tr("Updated on %1").replace("%1", formatted)

    def _thumbnail_ready(self, key: str, _image: QImage) -> None:
        for row, summary in enumerate(self.summaries, start=1):
            if any(str(photo) == key for photo, _ in summary.cover):
                index = self.index(row)
                self.dataChanged.emit(index, index, [COVER_ROLE])


def card_rect(cell: QRect, size: QSize) -> QRect:
    card = QRect(cell.topLeft(), size)
    card.moveCenter(cell.center())
    return card


def menu_rect(card: QRect) -> QRect:
    """The "⋯" button in the top-right corner of a card."""
    return QRect(card.right() - 8 - MENU_SIZE, card.top() + 8, MENU_SIZE, MENU_SIZE)


def cover_tiles(rect: QRect, count: int) -> list[QRect]:
    """Layout of the cover mosaic: 1 full, 2 side by side, 3 one big + two, 4 a 2×2 grid."""
    gap = 2
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    half_w, half_h = (w - gap) // 2, (h - gap) // 2
    right_x, bottom_y = x + half_w + gap, y + half_h + gap
    right_w, bottom_h = w - half_w - gap, h - half_h - gap
    if count <= 1:
        return [QRect(rect)] if count else []
    if count == 2:
        return [QRect(x, y, half_w, h), QRect(right_x, y, right_w, h)]
    if count == 3:
        return [
            QRect(x, y, half_w, h),
            QRect(right_x, y, right_w, half_h),
            QRect(right_x, bottom_y, right_w, bottom_h),
        ]
    return [
        QRect(x, y, half_w, half_h),
        QRect(right_x, y, right_w, half_h),
        QRect(x, bottom_y, half_w, bottom_h),
        QRect(right_x, bottom_y, right_w, bottom_h),
    ]


def draw_cropped(painter: QPainter, target: QRect, image: QImage) -> None:
    """Fill ``target`` with the centre of ``image`` (no letterboxing)."""
    size = image.size().scaled(target.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding)
    sx, sy = image.width() / size.width(), image.height() / size.height()
    source = QRectF(
        (size.width() - target.width()) / 2 * sx,
        (size.height() - target.height()) / 2 * sy,
        target.width() * sx,
        target.height() * sy,
    )
    painter.drawImage(QRectF(target), image, source)


class SelectionCardDelegate(QStyledItemDelegate):
    def __init__(self, view: SelectionCardView) -> None:
        super().__init__(view)
        self.view = view

    def sizeHint(self, option, index) -> QSize:
        return self.view.gridSize() - QSize(SPACING, SPACING)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        palette = option.palette
        card = card_rect(option.rect, self.sizeHint(option, index))
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        current = bool(option.state & QStyle.StateFlag.State_HasFocus) and self.view.hasFocus()
        accent = theme.ACCENT

        if index.data(SUMMARY_ROLE) is None:
            self._paint_new(painter, card, palette, hovered or current, accent)
        else:
            self._paint_selection(painter, card, index, palette, hovered)
            if hovered or current:
                painter.setPen(QPen(accent if current else theme.BORDER_STRONG, 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(QRectF(card).adjusted(1, 1, -1, -1), RADIUS, RADIUS)
                self._paint_menu_button(painter, menu_rect(card))
        painter.restore()

    def _paint_menu_button(self, painter: QPainter, rect: QRect) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.OVERLAY_HOVER)
        painter.drawEllipse(rect)
        icon = QRect(0, 0, 18, 18)
        icon.moveCenter(rect.center())
        theme.icon("ellipsis", QColor("white")).paint(painter, icon)

    def _paint_new(self, painter, card: QRect, palette, active: bool, accent: QColor) -> None:
        color = accent if active else theme.TEXT_MUTED
        pen = QPen(accent if active else theme.BORDER_STRONG, 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(theme.SURFACE if active else Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(card).adjusted(1, 1, -1, -1), RADIUS, RADIUS)
        # Round "+" badge above the label.
        badge = QRect(0, 0, 52, 52)
        badge.moveCenter(QPoint(card.center().x(), card.center().y() - 22))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent if active else theme.SURFACE_2)
        painter.drawEllipse(badge)
        icon = QRect(0, 0, 26, 26)
        icon.moveCenter(badge.center())
        theme.icon("plus", theme.ON_ACCENT if active else theme.TEXT).paint(painter, icon)
        painter.setPen(color)
        font = QFont(self.view.font())
        font.setBold(True)
        painter.setFont(font)
        label = QRect(card.left(), card.center().y() + 16, card.width(), 30)
        painter.drawText(
            label, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self.view.new_label()
        )

    def _paint_selection(
        self, painter, card: QRect, index: QModelIndex, palette, hovered: bool = False
    ) -> None:
        outline = QPainterPath()
        outline.addRoundedRect(QRectF(card), RADIUS, RADIUS)
        painter.fillPath(outline, theme.SURFACE_2 if hovered else theme.SURFACE)

        cover = QRect(card.left(), card.top(), card.width(), card.height() - TEXT_HEIGHT)
        painter.save()
        painter.setClipPath(outline)
        images = index.data(COVER_ROLE) or []
        if not images:
            painter.fillRect(cover, theme.SURFACE_2)
            icon = QRect(0, 0, 40, 40)
            icon.moveCenter(cover.center())
            theme.icon("images", theme.TEXT_FAINT).paint(painter, icon)
        for tile, image in zip(cover_tiles(cover, len(images)), images, strict=True):
            if image is not None and not image.isNull():
                draw_cropped(painter, tile, image)
            else:
                painter.fillRect(tile, theme.SURFACE_2)
        painter.restore()

        painter.setPen(QPen(theme.BORDER, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(outline)

        text = card.adjusted(12, card.height() - TEXT_HEIGHT + 8, -12, -8)
        line = text.height() // 3
        font = QFont(self.view.font())
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(theme.TEXT)
        name = painter.fontMetrics().elidedText(
            index.data(Qt.ItemDataRole.DisplayRole), Qt.TextElideMode.ElideRight, text.width()
        )
        painter.drawText(QRect(text.left(), text.top(), text.width(), line), 0, name)
        painter.setFont(self.view.font())
        painter.drawText(
            QRect(text.left(), text.top() + line, text.width(), line), 0, index.data(DETAILS_ROLE)
        )
        painter.setPen(theme.TEXT_MUTED)
        painter.drawText(
            QRect(text.left(), text.top() + 2 * line, text.width(), line),
            0,
            index.data(UPDATED_ROLE),
        )


class SelectionCardView(QListView):
    """Click or Enter on a card asks to open it (``open_requested``); the "⋯" button, right
    click and the menu key ask for its actions (``menu_requested``); F2 and Delete ask to
    rename or delete the current selection."""

    open_requested = Signal(QModelIndex)
    menu_requested = Signal(QModelIndex, QPoint)
    rename_requested = Signal(QModelIndex)
    delete_requested = Signal(QModelIndex)

    def __init__(self, loader: ThumbnailLoader, parent=None) -> None:
        super().__init__(parent)
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setWrapping(True)
        self.setUniformItemSizes(True)
        self.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self.setFrameShape(QListView.Shape.NoFrame)
        self.setMouseTracking(True)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAutoFillBackground(False)
        self.viewport().setAutoFillBackground(False)
        self.card_model = SelectionCardModel(loader, self)
        self.setModel(self.card_model)
        self.setItemDelegate(SelectionCardDelegate(self))
        self._update_grid()

    def new_label(self) -> str:
        return self.card_model.data(self.card_model.index(0))

    def is_selection_card(self, index: QModelIndex) -> bool:
        return index.isValid() and index.row() > 0

    def menu_button_rect(self, index: QModelIndex) -> QRect:
        return menu_rect(
            card_rect(self.visualRect(index), self.gridSize() - QSize(SPACING, SPACING))
        )

    def keyPressEvent(self, event) -> None:
        index = self.currentIndex()
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and index.isValid():
            self.open_requested.emit(index)
            return
        if self.is_selection_card(index):
            if key == Qt.Key.Key_F2:
                self.rename_requested.emit(index)
                return
            if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                self.delete_requested.emit(index)
                return
        super().keyPressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        pos = event.position().toPoint()
        index = self.indexAt(pos)
        super().mouseReleaseEvent(event)
        if event.button() != Qt.MouseButton.LeftButton or not index.isValid():
            return
        if self.is_selection_card(index) and self.menu_button_rect(index).contains(pos):
            self.setCurrentIndex(index)
            corner = self.menu_button_rect(index).bottomLeft()
            self.menu_requested.emit(index, self.viewport().mapToGlobal(corner))
        else:
            self.open_requested.emit(index)

    def contextMenuEvent(self, event) -> None:
        index = self.indexAt(event.pos()) if event.reason() == event.Reason.Mouse else None
        if index is None:
            index = self.currentIndex()
            pos = self.viewport().mapToGlobal(self.visualRect(index).center())
        else:
            pos = event.globalPos()
        if self.is_selection_card(index):
            self.setCurrentIndex(index)
            self.menu_requested.emit(index, pos)

    def mouseDoubleClickEvent(self, event) -> None:
        # The first click already opened the card.
        event.accept()

    def _update_grid(self) -> None:
        available = max(MIN_CARD, self.viewport().width() - 4)
        columns = max(1, available // (MIN_CARD + SPACING))
        width = min(MAX_CARD, available // columns - SPACING)
        cover = width * 2 // 3
        self.setGridSize(QSize(width + SPACING, cover + TEXT_HEIGHT + SPACING))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_grid()
