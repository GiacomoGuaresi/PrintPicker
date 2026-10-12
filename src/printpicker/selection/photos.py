"""Per-photo data of a selection: hash cache."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from printpicker.core.analysis import hash_photos
from printpicker.core.scanner import PhotoFile, scan
from printpicker.selection.sources import Source

_SIGN = 1 << 63


def to_db_hash(h: int | None) -> int | None:
    """SQLite integers are signed 64-bit: store the unsigned hash in two's complement."""
    return None if h is None else (h - (1 << 64) if h >= _SIGN else h)


def from_db_hash(h: int | None) -> int | None:
    return None if h is None else (h + (1 << 64) if h < 0 else h)


@dataclass(frozen=True)
class _Stat:
    size: int
    mtime_ns: int


def _stat(path) -> _Stat | None:
    try:
        st = os.stat(path)
    except OSError:
        return None
    return _Stat(st.st_size, st.st_mtime_ns)


# progress(done, total)
ProgressCallback = Callable[[int, int], None]

_COMMIT_EVERY = 25


def thumb_name(rel_path: str) -> str:
    return hashlib.sha1(rel_path.encode()).hexdigest() + ".jpg"


class PhotosMixin:
    """Photo scanning and hash caching for :class:`~printpicker.selection.store.Selection`."""

    def thumb_path(self, source: Source, rel_path: str) -> Path:
        """Cached thumbnail of a photo (it may not exist yet)."""
        return self.thumbs_dir / str(source.id) / thumb_name(rel_path)

    def analyze_source(
        self,
        source: Source,
        progress: ProgressCallback | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> list[tuple[PhotoFile, int | None]]:
        """Scan ``source`` and return ``(photo, hash)`` in scan order.

        Hashes are reused from the database when the file size and modification time are
        unchanged; only new or modified photos are decoded. Returns early (with what has been
        hashed so far) when ``cancelled()`` becomes true.
        """
        photos = list(scan(source.path))
        cached = {
            rel: (size, mtime, from_db_hash(h), bool(hashed))
            for rel, size, mtime, h, hashed in self.conn.execute(
                "SELECT rel_path, size, mtime_ns, hash, hashed FROM photos WHERE source_id = ?",
                (source.id,),
            )
        }
        hashes: dict[str, int | None] = {}
        stale: list[tuple[PhotoFile, _Stat | None]] = []
        for photo in photos:
            st = _stat(photo.absolute(source.path))
            c = cached.get(photo.rel_path)
            if c and c[3] and st and (c[0], c[1]) == (st.size, st.mtime_ns):
                hashes[photo.rel_path] = c[2]
            else:
                stale.append((photo, st))

        total = len(photos)
        done = total - len(stale)
        if progress:
            progress(done, total)
        stats = {p.rel_path: st for p, st in stale}
        pending = 0
        try:
            photo_iter = (p for p, _ in stale)
            thumb_for = lambda p: self.thumb_path(source, p.rel_path)  # noqa: E731
            for photo, h in hash_photos(source.path, photo_iter, thumb_for=thumb_for):
                st = stats[photo.rel_path]
                self.conn.execute(
                    "INSERT INTO photos (source_id, rel_path, size, mtime_ns, hash, hashed) "
                    "VALUES (?, ?, ?, ?, ?, 1) ON CONFLICT(source_id, rel_path) DO UPDATE SET "
                    "size = excluded.size, mtime_ns = excluded.mtime_ns, "
                    "hash = excluded.hash, hashed = 1",
                    (
                        source.id,
                        photo.rel_path,
                        st.size if st else None,
                        st.mtime_ns if st else None,
                        to_db_hash(h),
                    ),
                )
                hashes[photo.rel_path] = h
                done += 1
                pending += 1
                if pending >= _COMMIT_EVERY:
                    self.conn.commit()
                    pending = 0
                if progress:
                    progress(done, total)
                if cancelled and cancelled():
                    break
        finally:
            self.conn.commit()
        return [(p, hashes[p.rel_path]) for p in photos if p.rel_path in hashes]
