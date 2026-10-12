"""Pillow -> Qt image conversion."""

from __future__ import annotations

from PIL import Image
from PySide6.QtGui import QImage


def to_qimage(img: Image.Image) -> QImage:
    rgb = img if img.mode == "RGB" else img.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    qimage = QImage(data, rgb.width, rgb.height, 3 * rgb.width, QImage.Format.Format_RGB888)
    return qimage.copy()  # detach from the Python buffer
