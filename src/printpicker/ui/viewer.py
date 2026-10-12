"""Full-screen preview of the photos of a group."""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QRect, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPalette, QPen, QPixmap
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
    def __init__(self, relay: _Relay, row: int, path: Path) -> None:
        super().__init__()
        self.setAutoDelete(False)  # kept in PhotoViewer._requests, so tryTake() is safe
        self.relay, self.row, self.path = relay, row, path

    def run(self) -> None:
        try:
            image = to_qimage(load_image(self.path))
        except ImageLoadError:
            image = QImage()
        self.relay.loaded.emit(self.row, image)


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

    def mouseDoubleClickEvent(self, event) -> None:
        """Toggle between "fit" and 100% (at least twice the fit), zooming on the click."""
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.fitted:
            self.set_zoom(max(1.0, self.fit_zoom() * 2))
        else:
            self.fit()

    def wheelEvent(self, event) -> None:
        steps = event.angleDelta().y() / 120
        if steps:
            self.set_zoom(self.zoom() * ZOOM_STEP**steps)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.fitted:
            self.fit()


class PickedOverlay(QWidget):
    """Frame around the screen and a "✓ Picked" badge, shown while the photo is picked."""

    BORDER = 6
    MARGIN = 18

    def __init__(self, view: QGraphicsView) -> None:
        super().__init__(view.viewport())
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.text = ""
        view.viewport().installEventFilter(self)
        self.hide()

    def eventFilter(self, watched, event) -> bool:
        if event.type() == event.Type.Resize:
            self.setGeometry(watched.rect())
        return False

    def badge_rect(self) -> QRect:
        metrics = self.fontMetrics()
        height = max(36, metrics.height() + 14)
        width = height + metrics.horizontalAdvance(self.text) + 14
        return QRect(self.width() - self.MARGIN - width, self.MARGIN, width, height)

    def paintEvent(self, event) -> None:
        accent = self.palette().color(QPalette.ColorRole.Highlight)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        half = self.BORDER / 2
        painter.setPen(QPen(accent, self.BORDER))
        painter.drawRect(self.rect().toRectF().adjusted(half, half, -half, -half))

        badge = self.badge_rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawRoundedRect(badge, badge.height() / 2, badge.height() / 2)
        r = badge.height() // 2
        center = QPoint(badge.left() + r + 2, badge.center().y())
        painter.setPen(QPen(QColor("white"), 3))
        painter.drawPolyline(
            [center + QPoint(-6, 0), center + QPoint(-2, 5), center + QPoint(6, -5)]
        )
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(badge.adjusted(2 * r, 0, -12, 0), Qt.AlignmentFlag.AlignCenter, self.text)


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
        self.full_image: QImage | None = None
        self._cache: dict[int, QImage] = {}  # full images of the current photo and neighbours
        self._requests: dict[int, _FullLoad] = {}  # queued or running loads
        self._closed = False
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self._relay = _Relay()
        self._relay.loaded.connect(self._on_loaded)

        self.view = ImageView()
        self.view.zoom_changed.connect(self._update_caption)
        self.view.show_crop = show_crop
        self.picked_overlay = PickedOverlay(self.view)
        self.picked_overlay.text = self.tr("Picked")
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
        step = row - self.row
        self.row = row
        self.view.reset_view()
        self.full_image = None
        cached = self._cache.get(row)
        if cached is not None and not cached.isNull():
            self.full_image = cached
            self.view.set_image(cached)
        else:
            thumb = self.thumbnail_for(self.photos[row])
            self.view.set_image(thumb if thumb is not None else QImage())
        self._preload(ahead=-1 if step < 0 else 1)
        self._update_caption()

    def _wanted(self, ahead: int) -> list[int]:
        """Rows to keep loaded, most urgent first: current, next in browsing direction, previous."""
        rows = [self.row, self.row + ahead, self.row - ahead]
        return [r for r in rows if 0 <= r < len(self.photos)]

    def _preload(self, ahead: int) -> None:
        wanted = self._wanted(ahead)
        self._cache = {r: img for r, img in self._cache.items() if r in wanted}
        # Unqueue the loads not started yet, then queue what is missing by urgency.
        for r, job in list(self._requests.items()):
            if self.pool.tryTake(job):
                del self._requests[r]
        for priority, r in zip((2, 1, 0), wanted, strict=False):
            if r not in self._cache and r not in self._requests:
                job = _FullLoad(self._relay, r, self.paths_for(self.photos[r])[0])
                self._requests[r] = job
                self.pool.start(job, priority)

    def _on_loaded(self, row: int, image: QImage) -> None:
        self._requests.pop(row, None)
        if self._closed or abs(row - self.row) > 1:
            return
        self._cache[row] = image
        if row == self.row and not image.isNull():
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
        self.picked_overlay.setVisible(photo.rel_path in self.picked)
        mark = ""
        pixmap = self.view.item.pixmap()
        if not pixmap.isNull() and needs_crop(pixmap.width(), pixmap.height()):
            mark += "  ·  ✂ " + self.tr("will be cropped to 10×15")
        zoom = "" if self.view.fitted else f"  ·  {self.view.zoom():.0%}"
        self.caption.setText(f"{self.row + 1} / {len(self.photos)}  ·  {photo.name}{mark}{zoom}")

    def done(self, result: int) -> None:
        self._closed = True
        self.pool.clear()
        self.pool.waitForDone()
        super().done(result)
