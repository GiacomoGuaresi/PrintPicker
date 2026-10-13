"""Per-photo data of a selection: similarity signature cache."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from printpicker.core import embedding
from printpicker.core.analysis import analyze_photos
from printpicker.core.scanner import PhotoFile, scan
from printpicker.core.similarity import Signature
from printpicker.selection.sources import Source

_SIGN = 1 << 63


def to_db_hash(h: int | None) -> int | None:
    """SQLite integers are signed 64-bit: store the unsigned hash in two's complement."""
    return None if h is None else (h - (1 << 64) if h >= _SIGN else h)


def from_db_hash(h: int | None) -> int | None:
    return None if h is None else (h + (1 << 64) if h < 0 else h)


def to_db_embedding(vector: np.ndarray | None) -> bytes | None:
    """Stored as float16: half the space, same groups."""
    return None if vector is None else vector.astype("<f2").tobytes()


def from_db_embedding(blob: bytes | None) -> np.ndarray | None:
    return None if blob is None else np.frombuffer(blob, dtype="<f2").astype(np.float32)


def from_db(h: int | None, blob: bytes | None) -> Signature | None:
    return None if h is None else Signature(from_db_hash(h), from_db_embedding(blob))


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


class SourceUnavailableError(OSError):
    """The source folder disappeared (e.g. the drive was disconnected) while working on it."""


class PhotosMixin:
    """Photo scanning and signature caching for :class:`~printpicker.selection.store.Selection`."""

    def known_photos(self, source: Source) -> list[str]:
        """Relative paths of the photos recorded for a source."""
        rows = self.conn.execute(
            "SELECT rel_path FROM photos WHERE source_id = ? ORDER BY id", (source.id,)
        )
        return [r[0] for r in rows]

    def thumb_path(self, source: Source, rel_path: str) -> Path:
        """Cached thumbnail of a photo (it may not exist yet)."""
        return self.thumbs_dir / str(source.id) / thumb_name(rel_path)

    def analyze_source(
        self,
        source: Source,
        progress: ProgressCallback | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> list[tuple[PhotoFile, Signature | None]]:
        """Scan ``source`` and return ``(photo, signature)`` in scan order.

        Signatures are reused from the database when the file size and modification time are
        unchanged; only new or modified photos are decoded, plus photos analysed before the
        embedding model was available. Returns early (with what has been analysed so far)
        when ``cancelled()`` becomes true.
        """
        photos = list(scan(source.path))
        cached = {
            rel: (size, mtime, h, blob, bool(hashed))
            for rel, size, mtime, h, blob, hashed in self.conn.execute(
                "SELECT rel_path, size, mtime_ns, hash, embedding, hashed FROM photos "
                "WHERE source_id = ?",
                (source.id,),
            )
        }
        model = embedding.available()
        signatures: dict[str, Signature | None] = {}
        stale: list[tuple[PhotoFile, _Stat | None]] = []
        for photo in photos:
            st = _stat(photo.absolute(source.path))
            c = cached.get(photo.rel_path)
            complete = c and (c[2] is None or c[3] is not None or not model)
            if complete and c[4] and st and (c[0], c[1]) == (st.size, st.mtime_ns):
                signatures[photo.rel_path] = from_db(c[2], c[3])
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
            for photo, sig in analyze_photos(source.path, photo_iter, thumb_for=thumb_for):
                st = stats[photo.rel_path]
                if sig is None and (st is None or not source.is_available):
                    # Not readable because the drive went away, not because the file is
                    # broken: do not remember it as unreadable.
                    if not source.is_available:
                        raise SourceUnavailableError(str(source.path))
                    continue
                self.conn.execute(
                    "INSERT INTO photos "
                    "(source_id, rel_path, size, mtime_ns, hash, embedding, hashed) "
                    "VALUES (?, ?, ?, ?, ?, ?, 1) ON CONFLICT(source_id, rel_path) DO UPDATE SET "
                    "size = excluded.size, mtime_ns = excluded.mtime_ns, "
                    "hash = excluded.hash, embedding = excluded.embedding, hashed = 1",
                    (
                        source.id,
                        photo.rel_path,
                        st.size if st else None,
                        st.mtime_ns if st else None,
                        to_db_hash(sig.phash) if sig else None,
                        to_db_embedding(sig.embedding) if sig else None,
                    ),
                )
                signatures[photo.rel_path] = sig
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
        return [(p, signatures[p.rel_path]) for p in photos if p.rel_path in signatures]
