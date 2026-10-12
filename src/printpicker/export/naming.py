"""File names of photos copied into a selection."""

from __future__ import annotations

from printpicker.core.formats import PASSTHROUGH_EXTENSIONS, extension

SEPARATOR = " - "
# Most file systems limit a name to 255 bytes; keep a margin for "_2"-style suffixes.
MAX_NAME_BYTES = 240

_FORBIDDEN = set('<>:"/\\|?*') | {chr(c) for c in range(32)}


def needs_conversion(name: str) -> bool:
    """True when the photo is saved as JPG instead of copied unchanged."""
    return extension(name) not in PASSTHROUGH_EXTENSIONS


def _clean(part: str) -> str:
    """Make a path component valid on every platform (e.g. ':' allowed on macOS, not Windows)."""
    return "".join("_" if c in _FORBIDDEN else c for c in part).strip().rstrip(".")


def output_name(source_name: str, rel_path: str) -> str:
    """Name of the copy of ``rel_path`` (POSIX, relative to the source) in the selection.

    The prefix is the photo's folder path relative to the source, parts joined by " - "; photos
    in the source root use the source name::

        2026/ALPE DEVERO/foto.jpg  ->  2026 - ALPE DEVERO - foto.jpg
        foto.jpg (source "Foto 2026")  ->  Foto 2026 - foto.jpg

    Formats that are converted get a ``.jpg`` extension.
    """
    *folders, filename = rel_path.split("/")
    prefix = SEPARATOR.join(_clean(f) for f in folders) if folders else _clean(source_name)

    dot = filename.rfind(".")
    stem, ext = (filename[:dot], filename[dot:]) if dot > 0 else (filename, "")
    if needs_conversion(filename):
        ext = ".jpg"
    stem = _clean(stem) or "photo"

    tail = f"{SEPARATOR}{stem}{ext}"
    budget = MAX_NAME_BYTES - len(tail.encode())
    if budget <= 0:
        return _truncate(f"{stem}", MAX_NAME_BYTES - len(ext.encode())) + ext
    prefix = _truncate(prefix, budget)
    return f"{prefix}{tail}" if prefix else f"{stem}{ext}"


def _truncate(text: str, max_bytes: int) -> str:
    encoded = text.encode()
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode(errors="ignore").rstrip(" -.")
