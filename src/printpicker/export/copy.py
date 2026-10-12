"""Copying photos into a selection folder without overwriting anything."""

from __future__ import annotations

import filecmp
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from printpicker.core.images import load_image
from printpicker.export.naming import needs_conversion

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


def convert_photo(source: Path, dest_dir: Path, name: str) -> ExportResult:
    """Save ``source`` (HEIC, RAW, TIFF, WebP, ...) as a high-quality JPG named ``name``.

    The orientation is applied to the pixels, and the colour profile is kept. Duplicate
    handling is the same as :func:`copy_photo`, comparing the converted output.
    """
    tmp = dest_dir / f".{name}.part"
    try:
        save_as_jpeg(load_image(source), tmp)
        for target in candidates(dest_dir, name):
            if not target.exists():
                os.replace(tmp, target)
                return ExportResult(target, skipped=False)
            if filecmp.cmp(tmp, target, shallow=False):
                return ExportResult(target, skipped=True)
    finally:
        tmp.unlink(missing_ok=True)
    raise AssertionError("unreachable")


JPEG_QUALITY = 95


def save_as_jpeg(img: Image.Image, path: Path) -> None:
    kwargs = {}
    if icc := img.info.get("icc_profile"):
        kwargs["icc_profile"] = icc
    img.save(path, format="JPEG", quality=JPEG_QUALITY, subsampling=0, optimize=True, **kwargs)


def export_photo(source: Path, dest_dir: Path, name: str) -> ExportResult:
    """Copy or convert ``source``, depending on its format."""
    if needs_conversion(source.name):
        return convert_photo(source, dest_dir, name)
    return copy_photo(source, dest_dir, name)
