"""Grouping photos of the same folder by visual similarity."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from printpicker.core.hashing import hamming
from printpicker.core.scanner import PhotoFile

DEFAULT_THRESHOLD = 12


@dataclass(frozen=True)
class Group:
    """Visually similar photos of one folder, in scan order. May hold a single photo."""

    folder: str
    photos: tuple[PhotoFile, ...]


def group_photos(
    items: Iterable[tuple[PhotoFile, int | None]], threshold: int = DEFAULT_THRESHOLD
) -> list[Group]:
    """Group ``(photo, hash)`` pairs given in scan order.

    Photos are only grouped with photos of the same folder. A photo joins the group holding its
    closest photo, if that distance is at most ``threshold``; otherwise it starts a new group.
    Photos without a hash (unreadable) are always alone. Groups are ordered by their first
    photo, so folders and file names keep the scan order.
    """
    folders: dict[str, list[list[tuple[PhotoFile, int | None]]]] = {}
    for photo, h in items:
        groups = folders.setdefault(photo.folder, [])
        best, best_distance = None, threshold + 1
        if h is not None:
            for group in groups:
                for _, other in group:
                    if other is not None:
                        d = hamming(h, other)
                        if d < best_distance:
                            best, best_distance = group, d
        if best is None:
            groups.append([(photo, h)])
        else:
            best.append((photo, h))

    return [
        Group(folder, tuple(photo for photo, _ in members))
        for folder, groups in folders.items()
        for members in groups
    ]
