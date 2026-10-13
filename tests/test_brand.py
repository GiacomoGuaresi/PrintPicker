from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "src" / "printpicker" / "resources"


def test_app_logo_matches_brand_source():
    source = (ROOT / "assets" / "brand" / "logo.svg").read_bytes()
    assert (RESOURCES / "logo.svg").read_bytes() == source


def test_icons_are_generated():
    icons = ROOT / "packaging" / "icons"
    ico = Image.open(icons / "printpicker.ico")
    assert {(16, 16), (32, 32), (256, 256)} <= ico.info["sizes"]
    assert Image.open(icons / "printpicker.png").size == (512, 512)
    assert (icons / "printpicker.icns").stat().st_size > 0
    assert Image.open(RESOURCES / "icon.png").size == (256, 256)


def test_linux_desktop_entry():
    entry = (ROOT / "packaging" / "linux" / "printpicker.desktop").read_text()
    assert 'Exec="@EXEC@"' in entry and "Icon=printpicker" in entry


def test_bundled_fonts_have_license():
    fonts = RESOURCES / "fonts"
    assert sorted(p.name for p in fonts.glob("Inter-*.ttf"))
    assert (fonts / "OFL.txt").exists()
