"""Application metadata: name, version, author, links. The single source for UI, builds and docs."""

from __future__ import annotations

import platform
import sys

from printpicker import __version__

APP_NAME = "PrintPicker"
TAGLINE = "Pick the best shots from your photo archive and get them ready for print."
AUTHOR = "Giacomo Guaresi"
COPYRIGHT_YEAR = 2026
COPYRIGHT = f"© {COPYRIGHT_YEAR} {AUTHOR}"
LICENSE_NAME = "MIT License"
BUNDLE_ID = "io.github.giacomoguaresi.printpicker"

GITHUB_REPO = "GiacomoGuaresi/PrintPicker"
REPO_URL = f"https://github.com/{GITHUB_REPO}"
ISSUES_URL = f"{REPO_URL}/issues"
NEW_ISSUE_URL = f"{ISSUES_URL}/new"
RELEASES_URL = f"{REPO_URL}/releases"
LICENSE_URL = f"{REPO_URL}/blob/main/LICENSE"
GUIDE_URL = f"{REPO_URL}#readme"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

__all__ = [
    "APP_NAME",
    "AUTHOR",
    "BUNDLE_ID",
    "COPYRIGHT",
    "GUIDE_URL",
    "ISSUES_URL",
    "LATEST_RELEASE_API",
    "LICENSE_NAME",
    "LICENSE_URL",
    "NEW_ISSUE_URL",
    "RELEASES_URL",
    "REPO_URL",
    "TAGLINE",
    "__version__",
    "build_info",
]


def _module_version(name: str) -> str:
    try:
        module = __import__(name)
    except Exception:  # noqa: BLE001 - any import failure just means "unknown"
        return "not available"
    return getattr(module, "__version__", "unknown")


def build_info() -> str:
    """Versions of the app and of what it runs on, for bug reports and the About dialog."""
    import PySide6
    from PySide6.QtCore import qVersion

    lines = [
        f"{APP_NAME} {__version__}",
        f"Python {platform.python_version()} ({sys.platform})",
        f"Qt {qVersion()} · PySide6 {PySide6.__version__}",
        f"ONNX Runtime {_module_version('onnxruntime')}",
        f"OS {platform.platform()} ({platform.machine()})",
        "Bundled build" if getattr(sys, "frozen", False) else "Run from source",
    ]
    return "\n".join(lines)
