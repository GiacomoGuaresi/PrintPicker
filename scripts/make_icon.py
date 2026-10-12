"""Draw the PrintPicker icon and write it in every format the builds need.

    uv run python scripts/make_icon.py

Writes ``src/printpicker/resources/icon.png`` (window icon) and ``packaging/icons/``
(``printpicker.icns`` for macOS, ``printpicker.ico`` for Windows, ``printpicker.png``).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SIZE = 1024
SCALE = 4  # draw larger, then downsample for smooth edges


def draw() -> Image.Image:
    s = SIZE * SCALE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def box(x0, y0, x1, y1):
        return [int(v * s) for v in (x0, y0, x1, y1)]

    # Background: rounded square with a vertical gradient (deep blue -> teal).
    gradient = Image.new("RGBA", (1, s))
    top, bottom = (31, 64, 150), (22, 160, 160)
    for y in range(s):
        t = y / (s - 1)
        gradient.putpixel(
            (0, y), tuple(int(a + (b - a) * t) for a, b in zip(top, bottom, strict=True)) + (255,)
        )
    gradient = gradient.resize((s, s))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        box(0.06, 0.06, 0.94, 0.94), radius=int(0.2 * s), fill=255
    )
    img.paste(gradient, (0, 0), mask)

    # A print behind (semi-transparent, composited), then the main print.
    behind = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(behind).rounded_rectangle(
        box(0.29, 0.18, 0.83, 0.64), radius=int(0.03 * s), fill=(255, 255, 255, 120)
    )
    img.alpha_composite(behind)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        box(0.17, 0.30, 0.73, 0.78), radius=int(0.03 * s), fill=(255, 255, 255, 255)
    )
    # Photo inside the print: sky, sun, mountains.
    d.rectangle(box(0.21, 0.34, 0.69, 0.70), fill=(120, 190, 240, 255))
    d.ellipse(box(0.55, 0.38, 0.63, 0.46), fill=(255, 205, 70, 255))
    d.polygon(
        [tuple(int(v * s) for v in p) for p in ((0.21, 0.70), (0.36, 0.48), (0.49, 0.70))],
        fill=(40, 110, 90, 255),
    )
    d.polygon(
        [tuple(int(v * s) for v in p) for p in ((0.38, 0.70), (0.53, 0.52), (0.69, 0.70))],
        fill=(30, 85, 75, 255),
    )

    # Check badge.
    d.ellipse(
        box(0.58, 0.58, 0.86, 0.86),
        fill=(255, 176, 32, 255),
        outline=(255, 255, 255, 255),
        width=int(0.018 * s),
    )
    d.line(
        [tuple(int(v * s) for v in p) for p in ((0.645, 0.725), (0.705, 0.785), (0.80, 0.665))],
        fill=(255, 255, 255, 255),
        width=int(0.04 * s),
        joint="curve",
    )
    return img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def main() -> None:
    icon = draw()
    out = ROOT / "packaging" / "icons"
    out.mkdir(parents=True, exist_ok=True)
    icon.save(out / "printpicker.png")
    icon.save(out / "printpicker.icns", format="ICNS")
    icon.save(
        out / "printpicker.ico",
        format="ICO",
        sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)],
    )
    res = ROOT / "src" / "printpicker" / "resources"
    res.mkdir(parents=True, exist_ok=True)
    icon.resize((256, 256), Image.Resampling.LANCZOS).save(res / "icon.png")


if __name__ == "__main__":
    main()
