"""Grid of the photos of one group, where the user picks the ones to print."""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import (
    QAbstractListModel,
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
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QListView, QStyle, QStyledItemDelegate, QStyleOptionViewItem

from printpicker.core.print_format import needs_crop, print_area
from printpicker.core.scanner import PhotoFile
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
    """Draws a thumbnail fitted in its cell, with a strong frame and a check when selected."""

    def __init__(self, view: GroupView) -> None:
        super().__init__(view)
        self.view = view

    def sizeHint(self, option, index) -> QSize:
        return self.view.gridSize() - QSize(SPACING, SPACING)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        palette = option.palette
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        accent = palette.color(QPalette.ColorRole.Highlight)

        cell = option.rect
        image_area = cell.adjusted(6, 6, -6, -6 - LABEL_HEIGHT)
        image: QImage | None = index.data(Qt.ItemDataRole.DecorationRole)
        if image is not None and not image.isNull():
            size = image.size().scaled(image_area.size(), Qt.AspectRatioMode.KeepAspectRatio)
            target = QRect(0, 0, size.width(), size.height())
            target.moveCenter(image_area.center())
            painter.drawImage(target, image)
            frame = target
        else:
            frame = image_area
            painter.fillRect(frame, palette.color(QPalette.ColorRole.AlternateBase))
            text = self.view.tr("Unreadable") if image is not None else "…"
            painter.setPen(palette.color(QPalette.ColorRole.PlaceholderText))
            painter.drawText(frame, Qt.AlignmentFlag.AlignCenter, text)

        if image is not None and not image.isNull():
            if self.view.show_crop:
                draw_crop_overlay(painter, QRectF(frame), image.width(), image.height())
            if needs_crop(image.width(), image.height()):
                draw_crop_badge(painter, frame)

        if selected:
            painter.setPen(QPen(accent, 5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(frame.adjusted(-2, -2, 2, 2))
            r = 14
            center = QPoint(frame.right() - r - 6, frame.top() + r + 6)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(accent)
            painter.drawEllipse(center, r, r)
            painter.setPen(QPen(QColor("white"), 3))
            painter.drawPolyline(
                [center + QPoint(-6, 0), center + QPoint(-2, 5), center + QPoint(6, -5)]
            )
        if option.state & QStyle.StateFlag.State_HasFocus and self.view.hasFocus():
            painter.setPen(QPen(palette.color(QPalette.ColorRole.Text), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(cell.adjusted(1, 1, -2, -2))

        label = cell.adjusted(4, cell.height() - LABEL_HEIGHT, -4, 0)
        painter.setPen(palette.color(QPalette.ColorRole.Text))
        name = painter.fontMetrics().elidedText(
            index.data(Qt.ItemDataRole.DisplayRole), Qt.TextElideMode.ElideMiddle, label.width()
        )
        painter.drawText(label, Qt.AlignmentFlag.AlignCenter, name)
        painter.restore()


def draw_crop_overlay(painter: QPainter, frame: QRectF, width: int, height: int) -> None:
    """Darken what the print service will cut away to fill the print format."""
    x, y, w, h = print_area(width, height)
    sx, sy = frame.width() / width, frame.height() / height
    kept = QRectF(frame.x() + x * sx, frame.y() + y * sy, w * sx, h * sy)
    outside = QPainterPath()
    outside.addRect(frame)
    inside = QPainterPath()
    inside.addRect(kept)
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 150))
    painter.drawPath(outside.subtracted(inside))
    painter.setPen(QPen(QColor(255, 255, 255, 200), 1, Qt.PenStyle.DashLine))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(kept)
    painter.restore()


def draw_crop_badge(painter: QPainter, frame: QRect) -> None:
    """Small warning in the bottom-left corner: the photo will be cropped when printed."""
    painter.save()
    badge = QRect(frame.left() + 6, frame.bottom() - 28, 24, 22)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 176, 32, 230))
    painter.drawRoundedRect(badge, 5, 5)
    painter.setPen(QColor(40, 30, 0))
    font = painter.font()
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, "✂")
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
    """Click selects one photo, Ctrl/Cmd+click adds or removes photos."""

    picked_changed = Signal()
    confirm_requested = Signal()
    back_requested = Signal()
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
        self.setSelectionMode(QListView.SelectionMode.ExtendedSelection)
        self.setFrameShape(QListView.Shape.NoFrame)
        self.show_crop = False
        self.photo_model = PhotoModel(loader, self)
        self.setModel(self.photo_model)
        self.setItemDelegate(PhotoDelegate(self))
        self.selectionModel().selectionChanged.connect(lambda *_: self.picked_changed.emit())
        self.doubleClicked.connect(lambda index: self.preview_requested.emit(index.row()))

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

    _MOVES = {
        Qt.Key.Key_Left: QListView.CursorAction.MoveLeft,
        Qt.Key.Key_Right: QListView.CursorAction.MoveRight,
        Qt.Key.Key_Up: QListView.CursorAction.MoveUp,
        Qt.Key.Key_Down: QListView.CursorAction.MoveDown,
        Qt.Key.Key_Home: QListView.CursorAction.MoveHome,
        Qt.Key.Key_End: QListView.CursorAction.MoveEnd,
    }

    def keyPressEvent(self, event) -> None:
        key = event.key()
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
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.confirm_requested.emit()
            return
        if key == Qt.Key.Key_C:
            self.set_show_crop(not self.show_crop)
            self.crop_toggled.emit(self.show_crop)
            return
        if key in (Qt.Key.Key_F, Qt.Key.Key_Z):
            self.preview_requested.emit(max(self.currentIndex().row(), 0))
            return
        if key == Qt.Key.Key_Backspace:
            self.back_requested.emit()
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

    def set_show_crop(self, show: bool) -> None:
        self.show_crop = show
        self.viewport().update()

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
