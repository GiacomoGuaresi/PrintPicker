"""Full-screen preview of the photos of a group."""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from printpicker.core.images import ImageLoadError, load_image
from printpicker.core.print_format import needs_crop
from printpicker.core.scanner import PhotoFile
from printpicker.ui.group_view import PathsFn, draw_crop_overlay
from printpicker.ui.qimage import to_qimage


class _Relay(QObject):
    loaded = Signal(int, QImage)


class _FullLoad(QRunnable):
    def __init__(self, relay: _Relay, token: int, path: Path) -> None:
        super().__init__()
        self.relay, self.token, self.path = relay, token, path

    def run(self) -> None:
        try:
            image = to_qimage(load_image(self.path))
        except ImageLoadError:
            image = QImage()
        self.relay.loaded.emit(self.token, image)


ZOOM_STEP = 1.25
MAX_ZOOM = 8.0  # relative to actual pixels


class ImageView(QGraphicsView):
    """Shows one image: fitted by default, with zoom (wheel, +/-), 100% and hand-drag panning."""

    zoom_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.item = QGraphicsPixmapItem()
        self.item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.scene().addItem(self.item)
        self.setBackgroundBrush(QColor(20, 20, 20))
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.fitted = True
        self.angle = 0  # view rotation in degrees, never applied to the files
        self.show_crop = False

    def set_image(self, image: QImage, natural_size=None) -> None:
        """Show ``image``; ``natural_size`` lets a thumbnail stand in for the full photo."""
        pixmap = QPixmap.fromImage(image)
        self.item.setPixmap(pixmap)
        if natural_size is not None and not pixmap.isNull() and pixmap.width():
            self.item.setScale(natural_size.width() / pixmap.width())
        else:
            self.item.setScale(1.0)
        self.scene().setSceneRect(self.item.sceneBoundingRect())
        if self.fitted:
            self.fit()

    # Zoom ---------------------------------------------------------------------------------

    def zoom(self) -> float:
        """Current zoom: 1.0 means one photo pixel per screen pixel."""
        t = self.transform()
        return math.hypot(t.m11(), t.m12()) * self.devicePixelRatioF()

    def fit_zoom(self) -> float:
        rect = self.item.sceneBoundingRect()
        if rect.isEmpty():
            return 1.0
        if self.angle % 180:
            rect = rect.transposed()
        view = self.viewport().rect()
        return min(view.width() / rect.width(), view.height() / rect.height()) * (
            self.devicePixelRatioF()
        )

    def fit(self) -> None:
        self.fitted = True
        self.resetTransform()
        self.rotate(self.angle)
        if not self.item.pixmap().isNull():
            self.fitInView(self.item, Qt.AspectRatioMode.KeepAspectRatio)
        self.zoom_changed.emit()

    def set_zoom(self, zoom: float) -> None:
        """Zoom to an absolute level, never below "fit" nor above :data:`MAX_ZOOM`."""
        if self.item.pixmap().isNull():
            return
        fit = self.fit_zoom()
        if zoom <= fit * 1.001:
            self.fit()
            return
        zoom = min(zoom, MAX_ZOOM)
        factor = zoom / self.zoom()
        self.fitted = False
        self.scale(factor, factor)
        self.zoom_changed.emit()

    def zoom_in(self) -> None:
        self.set_zoom(self.zoom() * ZOOM_STEP)

    def zoom_out(self) -> None:
        self.set_zoom(self.zoom() / ZOOM_STEP)

    def actual_size(self) -> None:
        self.set_zoom(1.0)

    def rotate_by(self, degrees: int) -> None:
        self.angle = (self.angle + degrees) % 360
        if self.fitted:
            self.fit()
        else:
            self.rotate(degrees)
            self.zoom_changed.emit()

    def reset_view(self) -> None:
        self.angle = 0
        self.fitted = True

    def set_show_crop(self, show: bool) -> None:
        self.show_crop = show
        self.viewport().update()

    def drawForeground(self, painter: QPainter, rect) -> None:
        pixmap = self.item.pixmap()
        if self.show_crop and not pixmap.isNull():
            draw_crop_overlay(
                painter, self.item.sceneBoundingRect(), pixmap.width(), pixmap.height()
            )

    def wheelEvent(self, event) -> None:
        steps = event.angleDelta().y() / 120
        if steps:
            self.set_zoom(self.zoom() * ZOOM_STEP**steps)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.fitted:
            self.fit()


class PhotoViewer(QDialog):
    """Full-screen view: Left/Right to browse the group, Space to pick, Esc or F to close.

    ``toggled(row)`` asks the group view to pick/unpick a photo; :meth:`set_picked` keeps
    the viewer in sync.
    """

    toggled = Signal(int)
    crop_toggled = Signal(bool)

    def __init__(
        self,
        photos: list[PhotoFile],
        paths_for: PathsFn,
        thumbnail_for,
        picked: set[str],
        row: int = 0,
        parent: QWidget | None = None,
        show_crop: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Preview"))
        self.photos = photos
        self.paths_for = paths_for
        self.thumbnail_for = thumbnail_for
        self.picked = set(picked)
        self.row = row
        self._token = 0
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self._relay = _Relay()
        self._relay.loaded.connect(self._on_loaded)

        self.view = ImageView()
        self.view.zoom_changed.connect(self._update_caption)
        self.view.show_crop = show_crop
        self.caption = QLabel()
        self.caption.setStyleSheet("color: #ddd; padding: 6px;")
        self.help = QLabel(
            self.tr("← → browse · Space pick · +/− zoom · 0 fit · 1 100% · R rotate · C crop · Esc")
        )
        self.help.setStyleSheet("color: #888; padding: 6px;")
        bar = QHBoxLayout()
        bar.addWidget(self.caption)
        bar.addStretch()
        bar.addWidget(self.help)
        bar_widget = QWidget()
        bar_widget.setLayout(bar)
        bar_widget.setStyleSheet("background: #141414;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view, 1)
        layout.addWidget(bar_widget)

        self.show_row(row)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key.Key_Left:
            self.show_row(self.row - 1)
        elif key == Qt.Key.Key_Right:
            self.show_row(self.row + 1)
        elif key == Qt.Key.Key_Space:
            self._toggle()
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.view.zoom_in()
        elif key == Qt.Key.Key_Minus:
            self.view.zoom_out()
        elif key == Qt.Key.Key_0:
            self.view.fit()
        elif key == Qt.Key.Key_1:
            self.view.actual_size()
        elif key == Qt.Key.Key_C:
            self.view.set_show_crop(not self.view.show_crop)
            self.crop_toggled.emit(self.view.show_crop)
        elif key == Qt.Key.Key_R:
            shift = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            self.view.rotate_by(-90 if shift else 90)
        elif key in (Qt.Key.Key_Escape, Qt.Key.Key_F, Qt.Key.Key_Z):
            self.accept()
        else:
            super().keyPressEvent(event)

    def show_row(self, row: int) -> None:
        if not 0 <= row < len(self.photos):
            return
        self.row = row
        self._token += 1
        self.view.reset_view()
        photo = self.photos[row]
        thumb = self.thumbnail_for(photo)
        if thumb is not None and not thumb.isNull():
            self.view.set_image(thumb)
        else:
            self.view.set_image(QImage())
        self.full_image: QImage | None = None
        self.pool.clear()
        self.pool.start(_FullLoad(self._relay, self._token, self.paths_for(photo)[0]))
        self._update_caption()

    def _on_loaded(self, token: int, image: QImage) -> None:
        if token == self._token and not image.isNull():
            self.full_image = image
            self.view.set_image(image)
            self._update_caption()

    def _toggle(self) -> None:
        rel = self.photos[self.row].rel_path
        self.picked.symmetric_difference_update({rel})
        self.toggled.emit(self.row)
        self._update_caption()

    def set_picked(self, picked: set[str]) -> None:
        self.picked = set(picked)
        self._update_caption()

    def _update_caption(self) -> None:
        photo = self.photos[self.row]
        mark = "  ✓ " + self.tr("picked") if photo.rel_path in self.picked else ""
        pixmap = self.view.item.pixmap()
        if not pixmap.isNull() and needs_crop(pixmap.width(), pixmap.height()):
            mark += "  ·  ✂ " + self.tr("will be cropped to 10×15")
        zoom = "" if self.view.fitted else f"  ·  {self.view.zoom():.0%}"
        self.caption.setText(f"{self.row + 1} / {len(self.photos)}  ·  {photo.name}{mark}{zoom}")

    def done(self, result: int) -> None:
        self._token += 1
        self.pool.clear()
        self.pool.waitForDone()
        super().done(result)
