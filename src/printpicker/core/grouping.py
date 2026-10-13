"""Grouping photos of the same folder by visual similarity."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np

from printpicker.core.scanner import PhotoFile
from printpicker.core.similarity import Signature, distance_matrix

DEFAULT_THRESHOLD = 14


@dataclass(frozen=True)
class Group:
    """Visually similar photos of one folder, in scan order. May hold a single photo."""

    folder: str
    photos: tuple[PhotoFile, ...]


class PhotoIndex:
    """Photos with their pairwise distances, computed once and grouped at any threshold.

    Distances are only computed within a folder, since photos of different folders are never
    grouped together.
    """

    def __init__(self, items: Iterable[tuple[PhotoFile, Signature | None]]) -> None:
        folders: dict[str, list[tuple[PhotoFile, Signature | None]]] = {}
        for photo, sig in items:
            folders.setdefault(photo.folder, []).append((photo, sig))
        self._folders = [
            (folder, [p for p, _ in members], distance_matrix([s for _, s in members]))
            for folder, members in folders.items()
        ]

    def groups(self, threshold: float = DEFAULT_THRESHOLD) -> list[Group]:
        """Group the photos given in scan order.

        A photo joins the group whose farthest photo is closest to it, if every photo of that
        group is within ``threshold``; otherwise it starts a new group.
        Unreadable photos are always alone. Groups are ordered by their first photo, so
        folders and file names keep the scan order.
        """
        groups = []
        for folder, photos, dist in self._folders:
            groups += [
                Group(folder, tuple(photos[i] for i in members))
                for members in _complete_linkage(dist, threshold)
            ]
        return groups


def _complete_linkage(dist: np.ndarray, threshold: float) -> list[list[int]]:
    n = len(dist)
    # farthest[g, i]: distance from photo i to the farthest photo of group g. Complete
    # linkage: a group cannot drift through a chain of slightly different shots.
    farthest = np.empty((n, n), dtype=np.float32)
    members: list[list[int]] = []
    for i in range(n):
        if members:
            candidates = farthest[: len(members), i]
            best = int(np.argmin(candidates))  # ties: the earlier group
            if candidates[best] <= threshold:
                members[best].append(i)
                np.maximum(farthest[best], dist[i], out=farthest[best])
                continue
        farthest[len(members)] = dist[i]
        members.append([i])
    return members


def group_photos(
    items: Iterable[tuple[PhotoFile, Signature | None]], threshold: float = DEFAULT_THRESHOLD
) -> list[Group]:
    """Group ``(photo, signature)`` pairs given in scan order (see :meth:`PhotoIndex.groups`)."""
    return PhotoIndex(items).groups(threshold)
