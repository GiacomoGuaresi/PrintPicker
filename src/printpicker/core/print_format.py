"""Print formats and the cropping a print service applies to fill them."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrintFormat:
    name: str
    long_side_cm: float
    short_side_cm: float

    @property
    def aspect(self) -> float:
        return self.long_side_cm / self.short_side_cm


PRINT_10X15 = PrintFormat("10×15", 15, 10)

# Differences below this are not noticeable on a print.
ASPECT_TOLERANCE = 0.03


def needs_crop(width: int, height: int, fmt: PrintFormat = PRINT_10X15) -> bool:
    """True when a ``width`` × ``height`` photo does not have the format's proportions."""
    if width <= 0 or height <= 0:
        return False
    aspect = max(width, height) / min(width, height)
    return abs(aspect - fmt.aspect) / fmt.aspect > ASPECT_TOLERANCE


def print_area(
    width: float, height: float, fmt: PrintFormat = PRINT_10X15
) -> tuple[float, float, float, float]:
    """Centred ``(x, y, w, h)`` area kept when filling the print (orientation follows the photo)."""
    landscape = width >= height
    target = fmt.aspect if landscape else 1 / fmt.aspect
    if width / height > target:
        w, h = height * target, height
    else:
        w, h = width, width / target
    return (width - w) / 2, (height - h) / 2, w, h
