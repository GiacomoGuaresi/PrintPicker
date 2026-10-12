"""Hashing many photos in parallel."""

from __future__ import annotations

import os
from collections import deque
from collections.abc import Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from printpicker.core.hashing import phash
from printpicker.core.images import ImageLoadError, load_image
from printpicker.core.scanner import PhotoFile

# Size the photo is decoded at for hashing: small enough to be fast, large enough to be stable.
HASH_DECODE_SIZE = 256


def hash_file(path: Path) -> int | None:
    """Perceptual hash of a photo file, or ``None`` if it cannot be read."""
    try:
        return phash(load_image(path, max_size=HASH_DECODE_SIZE))
    except ImageLoadError:
        return None


def default_workers() -> int:
    # Decoding releases the GIL in Pillow; I/O on external drives also benefits from overlap.
    return min(8, os.cpu_count() or 2)


def hash_photos(
    source_root: Path, photos: Iterable[PhotoFile], workers: int | None = None
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
            in_flight.append((photo, pool.submit(hash_file, photo.absolute(source_root))))
            if len(in_flight) >= workers * 2:
                done_photo, future = in_flight.popleft()
                yield done_photo, future.result()
        while in_flight:
            done_photo, future = in_flight.popleft()
            yield done_photo, future.result()
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
