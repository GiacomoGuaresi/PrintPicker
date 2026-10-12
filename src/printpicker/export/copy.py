"""Copying photos into a selection folder without overwriting anything."""

from __future__ import annotations

import filecmp
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# writer(destination) creates the file at ``destination``.
Writer = Callable[[Path], None]


@dataclass(frozen=True)
class ExportResult:
    path: Path
    skipped: bool  # an identical file was already there


def candidates(dest_dir: Path, name: str):
    """``name``, then ``stem_2.ext``, ``stem_3.ext``, ..."""
    yield dest_dir / name
    dot = name.rfind(".")
    stem, ext = (name[:dot], name[dot:]) if dot > 0 else (name, "")
    n = 2
    while True:
        yield dest_dir / f"{stem}_{n}{ext}"
        n += 1


def write_atomically(destination: Path, writer: Writer) -> None:
    """Write via a temporary file, so an interrupted copy never leaves a truncated photo."""
    tmp = destination.with_name(f".{destination.name}.part")
    try:
        writer(tmp)
        os.replace(tmp, destination)
    finally:
        tmp.unlink(missing_ok=True)


def copy_photo(source: Path, dest_dir: Path, name: str) -> ExportResult:
    """Copy ``source`` into ``dest_dir`` as ``name``.

    If a file with that name exists and has the same content, nothing is copied. If it differs,
    a ``_2``, ``_3``, ... suffix is used. Existing files are never overwritten.
    """
    for target in candidates(dest_dir, name):
        if not target.exists():
            write_atomically(target, lambda tmp: shutil.copy2(source, tmp))
            return ExportResult(target, skipped=False)
        if filecmp.cmp(source, target, shallow=False):
            return ExportResult(target, skipped=True)
    raise AssertionError("unreachable")
