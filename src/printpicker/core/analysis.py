"""Hashing many photos in parallel."""

from __future__ import annotations

import os
from collections import deque
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from printpicker.core.hashing import phash
from printpicker.core.images import ImageLoadError, load_image
from printpicker.core.scanner import PhotoFile

# Size the photo is decoded at for hashing: small enough to be fast, large enough to be stable.
HASH_DECODE_SIZE = 256


THUMBNAIL_SIZE = 512
THUMBNAIL_QUALITY = 85

# thumb_for(photo) -> where to save its thumbnail
ThumbPathFn = Callable[[PhotoFile], Path]


def hash_file(path: Path, thumb_path: Path | None = None) -> int | None:
    """Perceptual hash of a photo file, or ``None`` if it cannot be read.

    With ``thumb_path``, a thumbnail is saved from the same decode, so slow drives are read
    only once per photo.
    """
    try:
        if thumb_path is None:
            return phash(load_image(path, max_size=HASH_DECODE_SIZE))
        img = load_image(path, max_size=THUMBNAIL_SIZE)
    except ImageLoadError:
        return None
    try:
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(thumb_path, format="JPEG", quality=THUMBNAIL_QUALITY)
    except OSError:
        pass  # a missing thumbnail is regenerated on display
    return phash(img)


def default_workers() -> int:
    # Decoding releases the GIL in Pillow; I/O on external drives also benefits from overlap.
    return min(8, os.cpu_count() or 2)


def hash_photos(
    source_root: Path,
    photos: Iterable[PhotoFile],
    workers: int | None = None,
    thumb_for: ThumbPathFn | None = None,
) -> Iterator[tuple[PhotoFile, int | None]]:
    """Yield ``(photo, hash)`` for each photo, in input order, hashing in parallel.

    Only a few photos are in flight at a time, so closing the generator early (cancellation)
    stops promptly instead of waiting for the whole batch.
    """
    workers = workers or default_workers()
    pool = ThreadPoolExecutor(max_workers=workers)
    in_flight: deque[tuple[PhotoFile, Future[int | None]]] = deque()
    try:
        for photo in photos:
            thumb = thumb_for(photo) if thumb_for else None
            future = pool.submit(hash_file, photo.absolute(source_root), thumb)
            in_flight.append((photo, future))
            if len(in_flight) >= workers * 2:
                done_photo, future = in_flight.popleft()
                yield done_photo, future.result()
        while in_flight:
            done_photo, future = in_flight.popleft()
            yield done_photo, future.result()
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
