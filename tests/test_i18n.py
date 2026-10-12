import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLocale
from PySide6.QtWidgets import QApplication

from printpicker.ui.app import I18N_DIR, install_translations

ROOT = Path(__file__).resolve().parent.parent


def test_every_string_is_translated():
    tree = ET.parse(I18N_DIR / "printpicker_it.ts")
    unfinished = [
        m.find("source").text
        for m in tree.getroot().iter("message")
        if m.find("translation").get("type") in ("unfinished", "obsolete", "vanished")
    ]
    assert unfinished == []


def test_translations_are_up_to_date(tmp_path):
    """Every tr() string in the UI is in the .ts file (run scripts/update_translations.py)."""
    ts = tmp_path / "check.ts"
    sources = sorted(str(p) for p in (ROOT / "src" / "printpicker" / "ui").glob("*.py"))
    exe = "pyside6-lupdate.exe" if sys.platform == "win32" else "pyside6-lupdate"
    lupdate = Path(sys.executable).with_name(exe)
    subprocess.run([str(lupdate), *sources, "-ts", str(ts)], check=True, capture_output=True)
    current = {m.find("source").text for m in ET.parse(ts).getroot().iter("message")}
    committed = {
        m.find("source").text
        for m in ET.parse(I18N_DIR / "printpicker_it.ts").getroot().iter("message")
    }
    assert current <= committed


def test_italian_is_loaded(qtbot):
    app = QApplication.instance()
    translators = install_translations(
        app, QLocale(QLocale.Language.Italian, QLocale.Country.Italy)
    )
    try:
        assert QCoreApplication.translate("StartScreen", "Open") == "Apri"
        assert (
            QCoreApplication.translate("StartScreen", "%1  ·  %n photo(s)", "", 3)
            == "%1  ·  3 foto"
        )
    finally:
        for t in translators:
            app.removeTranslator(t)
    assert QCoreApplication.translate("StartScreen", "Open") == "Open"
