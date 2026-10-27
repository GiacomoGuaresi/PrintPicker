"""Crash log: keeps a trace of crashes and errors in a file, also in the windowed builds.

The bundled app has no console (on Windows ``sys.stderr`` is even None), so without this a crash
leaves nothing behind. The log collects native crashes (faulthandler), unhandled Python
exceptions (main thread, other threads and Qt slots) and Qt's warnings and fatal errors.
"""

from __future__ import annotations

import faulthandler
import os
import platform
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import TextIO

from printpicker.about import APP_NAME, __version__

LOG_NAME = "printpicker.log"
MAX_SIZE = 1_000_000  # bytes: an older, bigger log is started over

_log: TextIO | None = None


def log_dir() -> Path:
    """Where the log goes: the usual per-user place for logs on each platform."""
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / APP_NAME
    return Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / APP_NAME


def log_path() -> Path:
    return log_dir() / LOG_NAME


def write(text: str) -> None:
    if _log is None:
        return
    _log.write(f"[{datetime.now().isoformat(timespec='seconds')}] {text.rstrip()}\n")
    _log.flush()


def _excepthook(exc_type, exc, tb) -> None:
    write("Unhandled exception:\n" + "".join(traceback.format_exception(exc_type, exc, tb)))
    if sys.__excepthook__ and sys.__stderr__ is not None:
        sys.__excepthook__(exc_type, exc, tb)


def _thread_excepthook(args: threading.ExceptHookArgs) -> None:
    name = args.thread.name if args.thread else "?"
    text = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    write(f"Unhandled exception in thread {name}:\n{text}")


def _qt_message(mode, context, message: str) -> None:
    from PySide6.QtCore import QtMsgType

    if mode in (QtMsgType.QtDebugMsg, QtMsgType.QtInfoMsg):
        return
    write(f"Qt {mode.name.removeprefix('Qt').removesuffix('Msg').lower()}: {message}")


def install(path: Path | None = None) -> Path | None:
    """Start logging to ``path`` (default: ``log_path()``). Returns the file, or None if it
    cannot be written (the app then runs without a log)."""
    global _log
    path = path or log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > MAX_SIZE:
            path.unlink()
        _log = open(path, "a", encoding="utf-8", errors="replace")  # noqa: SIM115 - open for the app's lifetime
    except OSError:
        return None

    python = platform.python_version()
    write(f"{APP_NAME} {__version__} started · {platform.platform()} · Python {python}")
    faulthandler.enable(_log, all_threads=True)
    sys.excepthook = _excepthook
    threading.excepthook = _thread_excepthook
    # Qt prints exceptions raised in slots to sys.stderr, which is None in windowed builds.
    if sys.stderr is None:
        sys.stderr = _log
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115

    from PySide6.QtCore import qInstallMessageHandler

    qInstallMessageHandler(_qt_message)
    return path
