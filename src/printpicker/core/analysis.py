"""Hashing many photos in parallel."""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor
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
    """Yield ``(photo, hash)`` for each photo, in input order, hashing in parallel."""
    photos = list(photos)
    with ThreadPoolExecutor(max_workers=workers or default_workers()) as pool:
        yield from zip(
            photos, pool.map(lambda p: hash_file(p.absolute(source_root)), photos), strict=True
        )
