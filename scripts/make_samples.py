"""Build a local set of sample photos for manual testing and README screenshots.

    uv run python scripts/make_samples.py [--force]

Downloads free photos from Lorem Picsum (Unsplash License) and writes ``samples/``: a few
"trip" folders where some shots come in bursts (small shifts, exposure changes, a blurred
frame) so they form similarity groups, plus portrait / 4:3 / square shots for the crop
preview, every supported non-RAW format and a folder of edge cases. ``samples/`` is
git-ignored; downloads are cached in ``samples/.downloads`` and the output is deterministic.
"""

from __future__ import annotations

import argparse
import io
import json
import random
import shutil
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pillow_heif
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "samples"
CACHE = OUT / ".downloads"
LONG_SIDE = 2400


@dataclass(frozen=True)
class Shot:
    picsum_id: int
    burst: int = 1  # number of frames; > 1 adds near-duplicate variants
    ratio: tuple[int, int] = (3, 2)  # width:height of the final photo
    ext: str = ".jpg"


# folder -> shots, in shooting order.
FOLDERS: dict[str, list[Shot]] = {
    "Seaside 2025": [
        Shot(12, burst=3),
        Shot(13),
        Shot(14, burst=2),
        Shot(16, burst=4),
        Shot(77, ratio=(2, 3)),
        Shot(124, burst=2, ratio=(4, 3)),
        Shot(179, burst=3),
        Shot(199),
        Shot(218, burst=2, ext=".heic"),
        Shot(244, ratio=(2, 3)),
        Shot(275, burst=2),
    ],
    "Mountains 2025": [
        Shot(29, burst=3),
        Shot(28),
        Shot(66, burst=2),
        Shot(177, burst=3, ratio=(2, 3)),
        Shot(191),
        Shot(235, burst=2, ext=".png"),
        Shot(231, burst=3),
        Shot(256, ratio=(1, 1)),
        Shot(287, burst=2, ext=".webp"),
        Shot(15, ratio=(2, 3)),
    ],
    "City trip 2025": [
        Shot(49, burst=2),
        Shot(57, ratio=(2, 3)),
        Shot(164, burst=3, ratio=(4, 3)),
        Shot(43),
        Shot(238, burst=2),
        Shot(249, burst=2, ext=".tif"),
        Shot(259),
        Shot(274, ratio=(4, 3)),
        Shot(122, burst=2),
    ],
    "City trip 2025/Food": [
        Shot(63, burst=2, ratio=(1, 1)),
        Shot(30),
        Shot(225, burst=2, ratio=(4, 3)),
    ],
    # A real sequence from one photographer: similar but distinct shots.
    "Work desk": [Shot(i) for i in range(0, 10)],
}


def fetch(picsum_id: int) -> tuple[Image.Image, dict]:
    """The original photo (cached) and its Picsum metadata."""
    CACHE.mkdir(parents=True, exist_ok=True)
    meta_path = CACHE / f"{picsum_id}.json"
    img_path = CACHE / f"{picsum_id}.jpg"
    if not meta_path.exists():
        with urllib.request.urlopen(f"https://picsum.photos/id/{picsum_id}/info", timeout=30) as r:
            meta_path.write_bytes(r.read())
    meta = json.loads(meta_path.read_text())
    if not img_path.exists():
        w, h = meta["width"], meta["height"]
        scale = min(1.0, (LONG_SIDE * 1.15) / max(w, h))
        url = f"https://picsum.photos/id/{picsum_id}/{round(w * scale)}/{round(h * scale)}.jpg"
        print(f"  downloading {picsum_id} by {meta['author']}")
        with urllib.request.urlopen(url, timeout=60) as r:
            img_path.write_bytes(r.read())
    with Image.open(img_path) as img:
        return img.convert("RGB"), meta


def crop_to(
    img: Image.Image, ratio: tuple[int, int], rng: random.Random, jitter: float
) -> Image.Image:
    """Crop to ``ratio`` (slightly zoomed in so frames can be shifted by ``jitter``)."""
    w, h = img.size
    rw, rh = ratio
    cw, ch = (w, w * rh / rw) if w * rh / rw <= h else (h * rw / rh, h)
    zoom = 0.94
    cw, ch = cw * zoom, ch * zoom
    cx = (w - cw) / 2 + rng.uniform(-jitter, jitter) * w
    cy = (h - ch) / 2 + rng.uniform(-jitter, jitter) * h
    cx = min(max(cx, 0), w - cw)
    cy = min(max(cy, 0), h - ch)
    out = img.crop((round(cx), round(cy), round(cx + cw), round(cy + ch)))
    scale = LONG_SIDE / max(out.size)
    return out.resize((round(out.width * scale), round(out.height * scale)), Image.LANCZOS)


def variant(img: Image.Image, frame: int, rng: random.Random) -> Image.Image:
    """A near-duplicate of ``img`` as the ``frame``-th shot of a burst."""
    if frame % 3 == 2:
        img = img.filter(ImageFilter.GaussianBlur(radius=rng.uniform(3, 5)))  # missed focus
    img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.88, 1.12))
    img = ImageEnhance.Contrast(img).enhance(rng.uniform(0.92, 1.08))
    angle = rng.uniform(-1.2, 1.2)
    rotated = img.rotate(angle, resample=Image.BICUBIC, expand=False)
    m = round(max(img.size) * 0.02)  # crop away the rotated corners
    return rotated.crop((m, m, img.width - m, img.height - m)).resize(img.size, Image.LANCZOS)


def save(img: Image.Image, path: Path, taken: datetime, rng: random.Random) -> None:
    exif = Image.Exif()
    stamp = taken.strftime("%Y:%m:%d %H:%M:%S")
    exif[0x0110] = rng.choice(["PrintPicker Sample Camera", "Pixel Sample", "iPhone Sample"])
    exif[0x0132] = stamp
    exif.get_ifd(0x8769)[0x9003] = stamp  # DateTimeOriginal
    ext = path.suffix.lower()
    if ext == ".jpg":
        img.save(path, quality=88, exif=exif)
    elif ext == ".heic":
        pillow_heif.from_pillow(img).save(path, quality=80, exif=exif.tobytes())
    elif ext == ".png":
        img.save(path, exif=exif, optimize=True)
    elif ext == ".webp":
        img.save(path, quality=85, exif=exif)
    elif ext == ".tif":
        img.save(path, compression="tiff_lzw", exif=exif)
    else:
        raise ValueError(ext)


def build_folder(folder: str, shots: list[Shot], start: datetime, credits: dict) -> int:
    target = OUT / folder
    target.mkdir(parents=True, exist_ok=True)
    rng = random.Random(folder)
    taken = start
    n = 0
    for shot in shots:
        original, meta = fetch(shot.picsum_id)
        credits[shot.picsum_id] = meta
        base = crop_to(original, shot.ratio, rng, jitter=0)
        for frame in range(shot.burst):
            n += 1
            img = (
                base
                if frame == 0
                else variant(crop_to(original, shot.ratio, rng, jitter=0.012), frame, rng)
            )
            save(img, target / f"IMG_{1000 + n:04d}{shot.ext}", taken, rng)
            taken += timedelta(seconds=rng.uniform(0.4, 2.5))
        taken += timedelta(minutes=rng.uniform(3, 90))
    return n


def build_edge_cases(credits: dict) -> int:
    target = OUT / "Edge cases"
    target.mkdir(parents=True, exist_ok=True)
    rng = random.Random("edge")
    original, meta = fetch(10)
    credits[10] = meta
    img = crop_to(original, (3, 2), rng, jitter=0)

    # Stored rotated, with the EXIF orientation tag saying how to display it.
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90° CW to display
    img.transpose(Image.ROTATE_90).save(target / "exif_rotated.jpg", quality=88, exif=exif)
    # Tiny and huge.
    img.resize((480, 320)).save(target / "small.jpg", quality=88)
    img.resize((6000, 4000), Image.LANCZOS).save(target / "large.jpg", quality=85)
    # Grayscale and with transparency.
    img.convert("L").save(target / "grayscale.jpg", quality=88)
    rgba = img.resize((1200, 800)).convert("RGBA")
    rgba.putalpha(Image.linear_gradient("L").resize(rgba.size))
    rgba.save(target / "transparent.png")
    # Panorama (very wide) and odd names.
    crop_to(original, (3, 1), rng, jitter=0).save(target / "panorama.jpg", quality=88)
    img.resize((1200, 800)).save(target / "àccénti e spazi.JPG", quality=88)
    # Unreadable files: truncated JPEG, garbage with a photo extension.
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    (target / "truncated.jpg").write_bytes(buf.getvalue()[: len(buf.getvalue()) // 3])
    (target / "not_a_photo.png").write_bytes(b"this is not a PNG file\n")
    # Ignored: video, sidecar, hidden file, system folder.
    (target / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    (target / "IMG_0001.xmp").write_text("<x:xmpmeta/>\n")
    img.resize((300, 200)).save(target / "._hidden.jpg", quality=80)
    return 9


def write_credits(credits: dict) -> None:
    lines = [
        "# Sample photo credits",
        "",
        "Photos from [Lorem Picsum](https://picsum.photos), sourced from Unsplash and free to",
        "use under the [Unsplash License](https://unsplash.com/license). Near-duplicates are",
        "edited copies generated by `scripts/make_samples.py`.",
        "",
        "| Picsum id | Author | Original |",
        "|---|---|---|",
    ]
    for pid in sorted(credits):
        meta = credits[pid]
        lines.append(f"| {pid} | {meta['author']} | {meta['url']} |")
    (OUT / "CREDITS.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="rebuild the photos (keeps the cache)")
    args = parser.parse_args()

    if args.force:
        for child in OUT.iterdir() if OUT.exists() else []:
            if child != CACHE:
                shutil.rmtree(child) if child.is_dir() else child.unlink()
    elif OUT.exists() and any(p != CACHE for p in OUT.iterdir()):
        print(f"{OUT} already exists, use --force to rebuild", file=sys.stderr)
        return 1

    credits: dict = {}
    start = datetime(2025, 7, 12, 9, 30)
    total = 0
    for i, (folder, shots) in enumerate(FOLDERS.items()):
        print(folder)
        total += build_folder(folder, shots, start + timedelta(days=9 * i), credits)
    print("Edge cases")
    total += build_edge_cases(credits)
    write_credits(credits)
    print(f"{total} photos in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
