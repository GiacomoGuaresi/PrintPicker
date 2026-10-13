"""Render the PrintPicker logo and write it in every format the builds and the README need.

    uv run python scripts/make_icon.py

The source is ``assets/brand/logo.svg``. Writes:

- ``src/printpicker/resources/icon.png`` (window icon) and ``logo.svg`` (shown in the app);
- ``packaging/icons/``: ``printpicker.icns`` (macOS), ``printpicker.ico`` (Windows),
  ``printpicker.png`` (Linux, 512×512);
- ``docs/images/``: ``logo.png`` (README), ``banner.png`` (README header) and
  ``social-preview.png`` (GitHub repository settings → Social preview).
"""

from __future__ import annotations

import io
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image  # noqa: E402
from PySide6.QtCore import QBuffer, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QGuiApplication,
    QImage,
    QPainter,
    QRadialGradient,
)
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "brand" / "logo.svg"
RESOURCES = ROOT / "src" / "printpicker" / "resources"
FONTS = RESOURCES / "fonts"
ICONS = ROOT / "packaging" / "icons"
IMAGES = ROOT / "docs" / "images"

sys.path.insert(0, str(ROOT / "src"))
from printpicker.about import APP_NAME, TAGLINE  # noqa: E402

BG = QColor("#111315")
TEXT = QColor("#E7E9EC")
MUTED = QColor("#9198A1")
ACCENT = QColor("#22B5AA")


def render_logo(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(str(SOURCE)).render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def to_pil(image: QImage) -> Image.Image:
    buffer = QBuffer()
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGBA")


def font(size: int, weight: QFont.Weight) -> QFont:
    f = QFont("Inter")
    f.setPixelSize(size)
    f.setWeight(weight)
    return f


def render_banner(width: int, height: int) -> QImage:
    """Dark card with a soft glow, the logo and the name: README header and social preview."""
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(BG)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    title_font = font(int(height * 0.15), QFont.Weight.Bold)
    tagline_font = font(int(height * 0.045), QFont.Weight.Normal)
    platforms_font = font(int(height * 0.036), QFont.Weight.DemiBold)
    platforms = "macOS  ·  Windows  ·  Linux"

    # Centre logo + text as one block.
    logo = height * 0.5
    gap = height * 0.08
    text_w = min(
        width * 0.62,
        max(
            QFontMetrics(title_font).horizontalAdvance(APP_NAME),
            QFontMetrics(tagline_font).horizontalAdvance(TAGLINE),
        )
        + 8,  # slack so rounding never wraps the tagline
    )
    x = (width - logo - gap - text_w) / 2
    glow = QRadialGradient(QPointF(x + logo / 2, height / 2), height * 0.9)
    glow.setColorAt(0, QColor(34, 181, 170, 70))
    glow.setColorAt(1, QColor(34, 181, 170, 0))
    painter.fillRect(image.rect(), glow)
    QSvgRenderer(str(SOURCE)).render(painter, QRectF(x, (height - logo) / 2, logo, logo))
    text_x = x + logo + gap
    left = Qt.AlignmentFlag.AlignLeft

    painter.setPen(TEXT)
    painter.setFont(title_font)
    painter.drawText(
        QRectF(text_x, height * 0.29, text_w, height * 0.2),
        left | Qt.AlignmentFlag.AlignVCenter,
        APP_NAME,
    )
    painter.setPen(MUTED)
    painter.setFont(tagline_font)
    painter.drawText(
        QRectF(text_x, height * 0.5, text_w, height * 0.16),
        left | Qt.TextFlag.TextWordWrap,
        TAGLINE,
    )
    painter.setPen(ACCENT)
    painter.setFont(platforms_font)
    painter.drawText(QRectF(text_x, height * 0.66, text_w, height * 0.08), left, platforms)
    painter.end()
    return image


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841 - fonts need it
    for path in sorted(FONTS.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(path))

    ICONS.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)

    big = to_pil(render_logo(1024))
    # Small sizes are rendered from the vector source, not downscaled, so they stay sharp.
    ico_sizes = (16, 24, 32, 48, 64, 128, 256)
    big.save(
        ICONS / "printpicker.ico",
        format="ICO",
        sizes=[(s, s) for s in ico_sizes],
        append_images=[to_pil(render_logo(s)) for s in ico_sizes],
    )
    big.save(ICONS / "printpicker.icns", format="ICNS")
    to_pil(render_logo(512)).save(ICONS / "printpicker.png")

    to_pil(render_logo(256)).save(RESOURCES / "icon.png")
    shutil.copyfile(SOURCE, RESOURCES / "logo.svg")

    to_pil(render_logo(256)).save(IMAGES / "logo.png")
    render_banner(1280, 400).save(str(IMAGES / "banner.png"))
    render_banner(1280, 640).save(str(IMAGES / "social-preview.png"))
    for path in (ICONS, RESOURCES / "icon.png", IMAGES):
        print(f"  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
