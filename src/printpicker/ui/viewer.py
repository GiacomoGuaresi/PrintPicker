"""Full-screen preview of the photos of a group."""

from __future__ import annotations

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
from printpicker.core.scanner import PhotoFile
from printpicker.ui.group_view import PathsFn
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


class ImageView(QGraphicsView):
    """Shows one image, fitted to the view."""

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
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_image(self, image: QImage, natural_size=None) -> None:
        """Show ``image``; ``natural_size`` lets a thumbnail stand in for the full photo."""
        pixmap = QPixmap.fromImage(image)
        self.item.setPixmap(pixmap)
        if natural_size is not None and not pixmap.isNull() and pixmap.width():
            self.item.setScale(natural_size.width() / pixmap.width())
        else:
            self.item.setScale(1.0)
        self.scene().setSceneRect(self.item.sceneBoundingRect())
        self.fit()

    def fit(self) -> None:
        self.resetTransform()
        if not self.item.pixmap().isNull():
            self.fitInView(self.item, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fit()


class PhotoViewer(QDialog):
    """Full-screen view: Left/Right to browse the group, Space to pick, Esc or F to close.

    ``toggled(row)`` asks the group view to pick/unpick a photo; :meth:`set_picked` keeps
    the viewer in sync.
    """

    toggled = Signal(int)

    def __init__(
        self,
        photos: list[PhotoFile],
        paths_for: PathsFn,
        thumbnail_for,
        picked: set[str],
        row: int = 0,
        parent: QWidget | None = None,
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
        self.caption = QLabel()
        self.caption.setStyleSheet("color: #ddd; padding: 6px;")
        self.help = QLabel(self.tr("← → browse · Space pick · Esc close"))
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
        elif key in (Qt.Key.Key_Escape, Qt.Key.Key_F, Qt.Key.Key_Z):
            self.accept()
        else:
            super().keyPressEvent(event)

    def show_row(self, row: int) -> None:
        if not 0 <= row < len(self.photos):
            return
        self.row = row
        self._token += 1
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
        self.caption.setText(f"{self.row + 1} / {len(self.photos)}  ·  {photo.name}{mark}")

    def done(self, result: int) -> None:
        self._token += 1
        self.pool.clear()
        self.pool.waitForDone()
        super().done(result)
