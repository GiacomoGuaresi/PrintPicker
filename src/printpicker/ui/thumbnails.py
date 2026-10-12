"""Asynchronous thumbnail loading for the group view."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtGui import QImage

from printpicker.core.analysis import THUMBNAIL_QUALITY, THUMBNAIL_SIZE
from printpicker.core.images import ImageLoadError, load_image

MEMORY_CACHE_SIZE = 300


class _Relay(QObject):
    done = Signal(int, str, QImage)


class _LoadTask(QRunnable):
    def __init__(self, relay: _Relay, generation: int, key: str, photo: Path, thumb: Path):
        super().__init__()
        self.relay, self.generation, self.key = relay, generation, key
        self.photo, self.thumb = photo, thumb

    def run(self) -> None:
        image = QImage(str(self.thumb)) if self.thumb.is_file() else QImage()
        if image.isNull():
            try:
                img = load_image(self.photo, max_size=THUMBNAIL_SIZE)
                self.thumb.parent.mkdir(parents=True, exist_ok=True)
                img.save(self.thumb, format="JPEG", quality=THUMBNAIL_QUALITY)
                image = QImage(str(self.thumb))
            except (ImageLoadError, OSError):
                image = QImage()
        self.relay.done.emit(self.generation, self.key, image)


class ThumbnailLoader(QObject):
    """Loads thumbnails from the selection cache (creating missing ones) on a thread pool.

    ``ready(key, image)`` is emitted on the UI thread; a null image means the photo could not
    be read. Results requested before :meth:`reset` are discarded.
    """

    ready = Signal(str, QImage)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(4)
        self._relay = _Relay()
        self._relay.done.connect(self._on_done)
        self._generation = 0
        self._cache: OrderedDict[str, QImage] = OrderedDict()
        self._pending: set[str] = set()

    def reset(self) -> None:
        self._generation += 1
        self.pool.clear()
        self._cache.clear()
        self._pending.clear()

    def cached(self, key: str) -> QImage | None:
        image = self._cache.get(key)
        if image is not None:
            self._cache.move_to_end(key)
        return image

    def request(self, key: str, photo: Path, thumb: Path) -> QImage | None:
        """Return the thumbnail if in memory, otherwise load it and emit ``ready`` later."""
        image = self.cached(key)
        if image is not None:
            return image
        if key not in self._pending:
            self._pending.add(key)
            self.pool.start(_LoadTask(self._relay, self._generation, key, photo, thumb))
        return None

    def _on_done(self, generation: int, key: str, image: QImage) -> None:
        if generation != self._generation:
            return
        self._pending.discard(key)
        self._cache[key] = image
        while len(self._cache) > MEMORY_CACHE_SIZE:
            self._cache.popitem(last=False)
        self.ready.emit(key, image)

    def shutdown(self) -> None:
        self.reset()
        self.pool.waitForDone()
