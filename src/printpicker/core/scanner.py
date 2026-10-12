"""Recursive scanning of a source folder for supported photos."""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from printpicker.core.formats import is_supported

# System folders that never contain the user's photos.
IGNORED_DIRS = frozenset(
    {
        "system volume information",
        "$recycle.bin",
        "recycler",
        "lost+found",
        "@eadir",  # Synology thumbnails
    }
)

_NUMBER = re.compile(r"(\d+)")


def natural_key(name: str) -> tuple:
    """Sort key that orders names like Finder / Explorer: case-insensitive, numbers by value."""
    parts = tuple(
        (0, int(part), "") if part.isdigit() else (1, 0, part.casefold())
        for part in _NUMBER.split(name)
        if part
    )
    # Original name as last tie-breaker keeps the order total and deterministic.
    return parts, name


@dataclass(frozen=True, order=True)
class PhotoFile:
    """A photo inside a source folder, identified by its POSIX path relative to the source."""

    rel_path: str

    @property
    def folder(self) -> str:
        """Relative POSIX path of the containing folder ("" for the source root)."""
        head, _, _ = self.rel_path.rpartition("/")
        return head

    @property
    def name(self) -> str:
        return self.rel_path.rpartition("/")[2]

    def absolute(self, source_root: Path) -> Path:
        return source_root.joinpath(*self.rel_path.split("/"))


def _is_hidden(name: str) -> bool:
    return name.startswith(".")


def _entries(directory: Path) -> tuple[list[str], list[str]]:
    """Visible sub-directories and supported files of a directory, naturally sorted."""
    dirs: list[str] = []
    files: list[str] = []
    try:
        with os.scandir(directory) as it:
            for entry in it:
                name = entry.name
                if _is_hidden(name):
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if name.casefold() not in IGNORED_DIRS:
                            dirs.append(name)
                    elif entry.is_file() and is_supported(name):
                        files.append(name)
                except OSError:
                    continue
    except OSError:
        # Unreadable folder (permissions, disconnected drive): skip it.
        return [], []
    dirs.sort(key=natural_key)
    files.sort(key=natural_key)
    return dirs, files


def scan(source_root: Path) -> Iterator[PhotoFile]:
    """Yield supported photos under ``source_root``, recursively.

    Order: a folder's own photos first (by name), then its sub-folders depth-first (by name).
    Hidden files/folders and system folders are skipped; videos and other files are ignored.
    """
    source_root = Path(source_root)

    def walk(directory: Path, rel: str) -> Iterator[PhotoFile]:
        dirs, files = _entries(directory)
        for name in files:
            yield PhotoFile(f"{rel}/{name}" if rel else name)
        for name in dirs:
            yield from walk(directory / name, f"{rel}/{name}" if rel else name)

    yield from walk(source_root, "")
