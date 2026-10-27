"""``PrintPicker --self-test``: checks that a packaged build has everything it needs."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QCoreApplication, QLocale
from PySide6.QtWidgets import QApplication


def run_self_test(app: QApplication) -> int:
    from printpicker.core.analysis import analyze_file
    from printpicker.core.images import load_image
    from printpicker.ui.app import install_translations
    from printpicker.ui.main_window import MainWindow

    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as tmp:
        for ext, fmt in (
            ("jpg", "JPEG"),
            ("png", "PNG"),
            ("heic", "HEIF"),
            ("tiff", "TIFF"),
            ("webp", "WEBP"),
        ):
            path = Path(tmp) / f"x.{ext}"
            try:
                Image.new("RGB", (32, 24), (10, 20, 30)).save(path, format=fmt)
                ok = load_image(path).size == (32, 24) and analyze_file(path) is not None
            except Exception:
                ok = False
            checks.append((f"format {ext}", ok))
    try:
        from printpicker.core.embedding import EMBEDDING_SIZE, embed

        vector = embed(Image.new("RGB", (64, 48), (10, 20, 30)))
        checks.append(("embedding model", vector is not None and vector.shape == (EMBEDDING_SIZE,)))
    except Exception:
        checks.append(("embedding model", False))
    try:
        import rawpy

        checks.append(("rawpy / LibRaw " + str(rawpy.libraw_version), True))
    except Exception:
        checks.append(("rawpy / LibRaw", False))

    translators = install_translations(app, QLocale(QLocale.Language.Italian))
    checks.append(
        (
            "italian translation",
            QCoreApplication.translate("StartScreen", "Settings…") == "Impostazioni…",
        )
    )
    for t in translators:
        app.removeTranslator(t)
    from printpicker.ui.app import ICON_PATH

    checks.append(("app icon", ICON_PATH.is_file()))
    try:
        from printpicker.ui import theme

        image = theme.icon("check").pixmap(24).toImage()
        drawn = any(
            image.pixelColor(x, y).alpha()
            for x in range(image.width())
            for y in range(image.height())
        )
        checks.append(("svg icons", drawn and not theme.logo(64).isNull()))
        checks.append(("inter font", theme.load_fonts()))
    except Exception:
        checks.append(("svg icons", False))
    try:
        import ssl

        from printpicker.ui.update_checker import ssl_context

        has_certificates = ssl_context().cert_store_stats()["x509_ca"] > 0
        checks.append((f"TLS for update check ({ssl.OPENSSL_VERSION})", has_certificates))
    except Exception:
        checks.append(("TLS for update check", False))
    try:
        MainWindow().close()
        checks.append(("main window", True))
    except Exception:
        checks.append(("main window", False))

    for name, ok in checks:
        print(f"{'ok  ' if ok else 'FAIL'} {name}")
    return 0 if all(ok for _, ok in checks) else 1
