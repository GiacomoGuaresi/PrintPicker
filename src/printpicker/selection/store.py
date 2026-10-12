"""Creating, opening and listing selections on disk."""

from __future__ import annotations

import datetime as dt
import os
import sqlite3
import sys
from pathlib import Path

from printpicker.core.scanner import natural_key
from printpicker.selection.schema import migrate
from printpicker.selection.sources import SourcesMixin

DATA_DIR = ".printpicker"
DB_NAME = "selection.db"
THUMBS_DIR = "thumbs"

_FORBIDDEN_CHARS = set('<>:"/\\|?*') | {chr(c) for c in range(32)}
_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {
    f"{p}{i}" for p in ("COM", "LPT") for i in range(1, 10)
}


class InvalidSelectionError(Exception):
    """A folder is not a PrintPicker selection, or a selection name is not valid."""


class SelectionExistsError(Exception):
    """A folder with the requested selection name already exists."""


def default_selection_name(prefix: str = "Stampa", today: dt.date | None = None) -> str:
    return f"{prefix} {(today or dt.date.today()).isoformat()}"


def validate_name(name: str) -> str:
    """Return the cleaned name, or raise if it cannot be a folder name on every platform."""
    name = name.strip()
    if not name or name in {".", ".."}:
        raise InvalidSelectionError("empty name")
    if any(c in _FORBIDDEN_CHARS for c in name):
        raise InvalidSelectionError(f"name contains forbidden characters: {name!r}")
    if name.endswith("."):
        raise InvalidSelectionError("name cannot end with a dot")
    if name.startswith("."):
        raise InvalidSelectionError("name cannot start with a dot")
    if name.split(".")[0].upper() in _RESERVED_NAMES:
        raise InvalidSelectionError(f"reserved name: {name!r}")
    return name


def is_selection(folder: Path) -> bool:
    return (Path(folder) / DATA_DIR / DB_NAME).is_file()


def list_selections(base_dir: Path) -> list[Path]:
    """Selection folders directly inside ``base_dir``, sorted by name."""
    try:
        entries = [p for p in Path(base_dir).iterdir() if p.is_dir() and is_selection(p)]
    except OSError:
        return []
    return sorted(entries, key=lambda p: natural_key(p.name))


def _hide(path: Path) -> None:
    """Dot-folders are hidden on macOS/Linux; Windows needs the hidden attribute."""
    if sys.platform == "win32":
        import ctypes

        file_attribute_hidden = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(str(path), file_attribute_hidden)


class Selection(SourcesMixin):
    """An open selection: its folder and database connection."""

    def __init__(self, folder: Path, conn: sqlite3.Connection):
        self.folder = folder
        self.conn = conn

    @property
    def name(self) -> str:
        return self.folder.name

    @property
    def data_dir(self) -> Path:
        return self.folder / DATA_DIR

    @property
    def thumbs_dir(self) -> Path:
        return self.data_dir / THUMBS_DIR

    @classmethod
    def create(cls, base_dir: Path, name: str) -> Selection:
        name = validate_name(name)
        folder = Path(base_dir) / name
        if folder.exists():
            raise SelectionExistsError(str(folder))
        data_dir = folder / DATA_DIR
        (data_dir / THUMBS_DIR).mkdir(parents=True)
        _hide(data_dir)
        selection = cls(folder, _connect(data_dir / DB_NAME))
        selection.set_meta("created_at", dt.datetime.now().isoformat(timespec="seconds"))
        return selection

    @classmethod
    def open(cls, folder: Path) -> Selection:
        folder = Path(folder)
        if not is_selection(folder):
            raise InvalidSelectionError(f"not a selection: {folder}")
        (folder / DATA_DIR / THUMBS_DIR).mkdir(exist_ok=True)
        return cls(folder, _connect(folder / DATA_DIR / DB_NAME))

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> Selection:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def get_meta(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def set_meta(self, key: str, value: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(os.fspath(db_path), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn
