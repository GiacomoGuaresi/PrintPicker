"""Grid of the photos of one group, where the user picks the ones to print."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import (
    QAbstractListModel,
    QCoreApplication,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QPoint,
    QRect,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QListView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from printpicker.core.print_format import needs_crop, print_area
from printpicker.core.scanner import PhotoFile
from printpicker.ui import theme
from printpicker.ui.thumbnails import ThumbnailLoader

LABEL_HEIGHT = 20
SPACING = 12
MIN_CELL = 120
MAX_CELL = 900

# paths_for(photo) -> (photo file, thumbnail file)
PathsFn = Callable[[PhotoFile], tuple[Path, Path]]


class PhotoModel(QAbstractListModel):
    def __init__(self, loader: ThumbnailLoader, parent=None) -> None:
        super().__init__(parent)
        self.loader = loader
        self.photos: list[PhotoFile] = []
        self.paths_for: PathsFn | None = None
        loader.ready.connect(self._thumbnail_ready)

    def set_photos(self, photos: list[PhotoFile], paths_for: PathsFn) -> None:
        self.beginResetModel()
        self.photos = list(photos)
        self.paths_for = paths_for
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self.photos)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        photo = self.photos[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return photo.name
        if role == Qt.ItemDataRole.ToolTipRole:
            image = self.loader.cached(photo.rel_path)
            if image is not None and needs_crop(image.width(), image.height()):
                return self.tr("%1\nWill be cropped to fit a 10×15 print").replace(
                    "%1", photo.rel_path
                )
            return photo.rel_path
        if role == Qt.ItemDataRole.DecorationRole and self.paths_for is not None:
            return self.loader.request(photo.rel_path, *self.paths_for(photo))
        if role == Qt.ItemDataRole.UserRole:
            return photo
        return None

    def _thumbnail_ready(self, key: str, _image: QImage) -> None:
        for row, photo in enumerate(self.photos):
            if photo.rel_path == key:
                index = self.index(row)
                self.dataChanged.emit(index, index, [Qt.ItemDataRole.DecorationRole])


class PhotoDelegate(QStyledItemDelegate):
    """Draws a thumbnail fitted in its cell, with a checkbox and a strong frame when picked."""

    def __init__(self, view: GroupView) -> None:
        super().__init__(view)
        self.view = view

    def sizeHint(self, option, index) -> QSize:
        return self.view.gridSize() - QSize(SPACING, SPACING)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        focused = bool(option.state & QStyle.StateFlag.State_HasFocus) and self.view.hasFocus()

        cell = option.rect
        image: QImage | None = index.data(Qt.ItemDataRole.DecorationRole)
        frame = image_frame(cell, image)
        if image is not None and not image.isNull():
            painter.drawImage(frame, image)
        else:
            painter.fillRect(frame, theme.SURFACE_2)
            unreadable = QCoreApplication.translate("GroupView", "Unreadable")
            text = unreadable if image is not None else "…"
            painter.setPen(theme.TEXT_MUTED)
            painter.drawText(frame, Qt.AlignmentFlag.AlignCenter, text)

        if image is not None and not image.isNull() and self.view.show_crop:
            draw_crop_overlay(painter, QRectF(frame), image.width(), image.height())

        # Rings around the photo: amber when picked, teal for the keyboard cursor, grey on hover.
        painter.setBrush(Qt.BrushStyle.NoBrush)
        ring = QRectF(frame)
        if selected:
            painter.setPen(QPen(theme.PICK, 4))
            painter.drawRoundedRect(ring.adjusted(-3, -3, 3, 3), 4, 4)
        elif hovered:
            painter.setPen(QPen(theme.BORDER_STRONG, 2))
            painter.drawRoundedRect(ring.adjusted(-2, -2, 2, 2), 3, 3)
        if focused:
            painter.setPen(QPen(theme.ACCENT, 2))
            offset = 8 if selected else 5
            painter.drawRoundedRect(ring.adjusted(-offset, -offset, offset, offset), 6, 6)
        draw_checkbox(painter, frame, selected, hovered)
        if hovered:
            draw_preview_button(painter, frame)

        label = cell.adjusted(4, cell.height() - LABEL_HEIGHT, -4, 0)
        painter.setPen(theme.TEXT if selected else theme.TEXT_MUTED)
        name = painter.fontMetrics().elidedText(
            index.data(Qt.ItemDataRole.DisplayRole), Qt.TextElideMode.ElideMiddle, label.width()
        )
        painter.drawText(label, Qt.AlignmentFlag.AlignCenter, name)
        painter.restore()


def image_frame(cell: QRect, image: QImage | None) -> QRect:
    """Where the thumbnail is drawn in its cell (the whole image area while loading)."""
    area = cell.adjusted(6, 6, -6, -6 - LABEL_HEIGHT)
    if image is None or image.isNull():
        return area
    size = image.size().scaled(area.size(), Qt.AspectRatioMode.KeepAspectRatio)
    frame = QRect(0, 0, size.width(), size.height())
    frame.moveCenter(area.center())
    return frame


def preview_button_rect(frame: QRect) -> QRect:
    return QRect(frame.right() - 8 - 30, frame.top() + 8, 30, 30)


def draw_preview_button(painter: QPainter, frame: QRect) -> None:
    """Expand icon in the top-right corner, shown on hover: opens the full-screen preview."""
    painter.save()
    button = preview_button_rect(frame)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(theme.OVERLAY_HOVER)
    painter.drawRoundedRect(button, 6, 6)
    icon = QRect(0, 0, 18, 18)
    icon.moveCenter(button.center())
    theme.icon("maximize-2", QColor("white")).paint(painter, icon)
    painter.restore()


def draw_checkbox(painter: QPainter, frame: QRect, checked: bool, hovered: bool) -> None:
    """Checkbox in the top-left corner of the photo: always visible, so it's clear that a
    click picks the photo."""
    painter.save()
    box = QRect(frame.left() + 8, frame.top() + 8, 26, 26)
    if checked:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.PICK)
    else:
        painter.setPen(QPen(QColor(255, 255, 255, 230 if hovered else 190), 2))
        painter.setBrush(theme.OVERLAY_HOVER if hovered else theme.OVERLAY)
    painter.drawRoundedRect(box, 7, 7)
    if checked:
        c = box.center()
        painter.setPen(
            QPen(
                theme.ON_PICK,
                3,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.drawPolyline([c + QPoint(-6, 0), c + QPoint(-2, 4), c + QPoint(6, -4)])
    painter.restore()


def draw_crop_overlay(painter: QPainter, frame: QRectF, width: int, height: int) -> None:
    """Darken what the print service will cut away to fill the print format."""
    x, y, w, h = print_area(width, height)
    sx, sy = frame.width() / width, frame.height() / height
    kept = QRectF(frame.x() + x * sx, frame.y() + y * sy, w * sx, h * sy)
    if width - w < 0.5 and height - h < 0.5:
        return  # nothing is cut away
    outside = QPainterPath()
    outside.addRect(frame)
    inside = QPainterPath()
    inside.addRect(kept)
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 150))
    painter.drawPath(outside.subtracted(inside))
    painter.setPen(QPen(QColor(255, 255, 255, 110), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(kept)
    painter.restore()


def best_cell_size(count: int, width: int, height: int) -> int:
    """Largest square cell so that ``count`` cells fit in ``width`` × ``height``."""
    if count <= 0:
        return MIN_CELL
    best = MIN_CELL
    for columns in range(1, count + 1):
        rows = math.ceil(count / columns)
        cell = min(width // columns, (height // rows) if rows else height)
        best = max(best, cell)
    return min(best, MAX_CELL)


class GroupView(QListView):
    """Click picks or unpicks a photo (no modifier keys needed), double-click previews it."""

    picked_changed = Signal()
    next_requested = Signal()
    previous_requested = Signal()
    preview_requested = Signal(int)
    crop_toggled = Signal(bool)

    def __init__(self, loader: ThumbnailLoader, parent=None) -> None:
        super().__init__(parent)
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setWrapping(True)
        self.setUniformItemSizes(True)
        self.setSelectionMode(QListView.SelectionMode.MultiSelection)
        self.setMouseTracking(True)
        self.setTabKeyNavigation(True)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setFrameShape(QListView.Shape.NoFrame)
        palette = self.palette()
        palette.setColor(palette.ColorRole.Base, theme.BG)
        self.setPalette(palette)
        self.show_crop = True
        self._last_press: tuple[int, bool, float] = (-1, False, 0.0)
        self.photo_model = PhotoModel(loader, self)
        self.setModel(self.photo_model)
        self.setItemDelegate(PhotoDelegate(self))
        self.selectionModel().selectionChanged.connect(lambda *_: self.picked_changed.emit())

    def set_photos(self, photos: list[PhotoFile], paths_for: PathsFn, picked: set[str]) -> None:
        self.photo_model.set_photos(photos, paths_for)
        self._update_grid()
        selection = QItemSelection()
        for row, photo in enumerate(photos):
            if photo.rel_path in picked:
                index = self.photo_model.index(row)
                selection.select(index, index)
        self.selectionModel().select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
        if photos:
            self.selectionModel().setCurrentIndex(
                self.photo_model.index(0), QItemSelectionModel.SelectionFlag.NoUpdate
            )
        self.picked_changed.emit()

    def picked(self) -> set[str]:
        return {
            self.photo_model.photos[i.row()].rel_path
            for i in self.selectionModel().selectedIndexes()
        }

    # ← → switch group (see keyPressEvent); these move between the photos of the group.
    _MOVES = {
        Qt.Key.Key_Up: QListView.CursorAction.MoveUp,
        Qt.Key.Key_Down: QListView.CursorAction.MoveDown,
        Qt.Key.Key_Home: QListView.CursorAction.MoveHome,
        Qt.Key.Key_End: QListView.CursorAction.MoveEnd,
    }

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Right, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.next_requested.emit()
            return
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Backspace):
            self.previous_requested.emit()
            return
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            count = self.photo_model.rowCount()
            if count:
                step = 1 if key == Qt.Key.Key_Tab else -1
                row = (max(self.currentIndex().row(), 0) + step) % count
                self.selectionModel().setCurrentIndex(
                    self.photo_model.index(row), QItemSelectionModel.SelectionFlag.NoUpdate
                )
            return
        if key in self._MOVES and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # Arrows move the cursor without changing the picked photos.
            index = self.moveCursor(self._MOVES[key], event.modifiers())
            if index.isValid():
                self.selectionModel().setCurrentIndex(
                    index, QItemSelectionModel.SelectionFlag.NoUpdate
                )
            return
        if key == Qt.Key.Key_Space:
            self.toggle_current()
            return
        if key == Qt.Key.Key_A:
            self.pick_all(len(self.picked()) < self.photo_model.rowCount())
            return
        if key == Qt.Key.Key_C:
            self.set_show_crop(not self.show_crop)
            self.crop_toggled.emit(self.show_crop)
            return
        if key in (Qt.Key.Key_F, Qt.Key.Key_Z):
            self.preview_requested.emit(max(self.currentIndex().row(), 0))
            return
        if Qt.Key.Key_1 <= key <= Qt.Key.Key_9:
            row = key - Qt.Key.Key_1
            if row < self.photo_model.rowCount():
                self.selectionModel().setCurrentIndex(
                    self.photo_model.index(row), QItemSelectionModel.SelectionFlag.NoUpdate
                )
                self.toggle_current()
            return
        super().keyPressEvent(event)

    # The mouse is handled here rather than by QListView: a click always toggles one photo,
    # and dragging never selects a range.
    def mousePressEvent(self, event) -> None:
        self.setFocus()
        if event.button() == Qt.MouseButton.BackButton:
            self.previous_requested.emit()
            return
        if event.button() == Qt.MouseButton.ForwardButton:
            self.next_requested.emit()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        index = self.indexAt(pos)
        if not index.isValid():
            return
        frame = image_frame(self.visualRect(index), index.data(Qt.ItemDataRole.DecorationRole))
        if preview_button_rect(frame).contains(pos):
            self.preview_requested.emit(index.row())
            return
        # Remember the state before a click, but not before the second click of a
        # double-click: the double-click restores it, so previewing never changes the choice.
        now = time.monotonic()
        last_row, _, last_time = self._last_press
        interval = QApplication.doubleClickInterval() / 1000
        if not (index.row() == last_row and now - last_time < interval):
            self._last_press = (index.row(), self.is_picked(index.row()), now)
        self.selectionModel().setCurrentIndex(index, QItemSelectionModel.SelectionFlag.NoUpdate)
        self.toggle_row(index.row())

    def mouseMoveEvent(self, event) -> None:
        if not event.buttons():
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        pass

    def mouseDoubleClickEvent(self, event) -> None:
        index = self.indexAt(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and index.isValid():
            row, was_picked, _ = self._last_press
            if row == index.row() and self.is_picked(row) != was_picked:
                self.toggle_row(row)
            self.preview_requested.emit(index.row())

    def set_show_crop(self, show: bool) -> None:
        self.show_crop = show
        self.viewport().update()

    def pick_all(self, picked: bool) -> None:
        if picked:
            self.selectAll()
        else:
            self.clearSelection()

    def is_picked(self, row: int) -> bool:
        return self.selectionModel().isSelected(self.photo_model.index(row))

    def toggle_row(self, row: int) -> None:
        self.selectionModel().select(
            self.photo_model.index(row), QItemSelectionModel.SelectionFlag.Toggle
        )

    def toggle_current(self) -> None:
        index = self.currentIndex()
        if index.isValid():
            self.selectionModel().select(index, QItemSelectionModel.SelectionFlag.Toggle)

    def _update_grid(self) -> None:
        # Measure the full widget area: the cell size is chosen so that everything fits, so
        # the scroll bar is only needed for very large groups (cells at their minimum size).
        width, height = self.width() - 4, self.height() - 4
        count = self.photo_model.rowCount()
        cell = best_cell_size(count, width, height)
        columns = max(1, width // cell)
        fits = math.ceil(count / columns) * cell <= height if count else True
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff if fits else Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.setGridSize(QSize(cell, cell))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_grid()
