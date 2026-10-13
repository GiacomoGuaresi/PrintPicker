"""Debug command: scan a folder and print the similarity groups.

python -m printpicker.cli <folder> [--threshold N] [--sheets DIR] [--cache FILE]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

from printpicker.core.analysis import analyze_photos
from printpicker.core.grouping import DEFAULT_THRESHOLD, Group, group_photos
from printpicker.core.images import ImageLoadError, load_image
from printpicker.core.scanner import scan
from printpicker.core.similarity import from_json, to_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="printpicker.cli", description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path, help="source folder to analyse")
    parser.add_argument("-t", "--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--sheets", type=Path, help="write a contact sheet per multi-photo group")
    parser.add_argument("--cache", type=Path, help="JSON file to reuse the analysis between runs")
    args = parser.parse_args(argv)

    root: Path = args.folder
    if not root.is_dir():
        print(f"not a folder: {root}", file=sys.stderr)
        return 2

    started = time.monotonic()
    photos = list(scan(root))
    cache: dict[str, list | None] = {}
    if args.cache and args.cache.exists():
        cache = json.loads(args.cache.read_text())
    missing = [p for p in photos if p.rel_path not in cache]
    for i, (photo, sig) in enumerate(analyze_photos(root, missing), 1):
        cache[photo.rel_path] = to_json(sig)
        print(f"\ranalysing {i}/{len(missing)}", end="", file=sys.stderr)
    if missing:
        print(file=sys.stderr)
    if args.cache:
        args.cache.write_text(json.dumps(cache))

    groups = group_photos(((p, from_json(cache[p.rel_path])) for p in photos), args.threshold)
    elapsed = time.monotonic() - started

    multi = [g for g in groups if len(g.photos) > 1]
    for i, g in enumerate(groups, 1):
        names = ", ".join(p.name for p in g.photos)
        print(f"{i:4d} [{g.folder or '.'}] ({len(g.photos)}) {names}")
    print(
        f"\n{len(photos)} photos, {len(groups)} groups ({len(multi)} with 2+ photos, "
        f"{sum(len(g.photos) for g in multi)} photos in them), threshold {args.threshold}, "
        f"{elapsed:.1f}s"
    )

    if args.sheets:
        args.sheets.mkdir(parents=True, exist_ok=True)
        for i, g in enumerate(groups, 1):
            if len(g.photos) > 1:
                contact_sheet(root, g).save(args.sheets / f"group_{i:04d}.jpg", quality=85)
        print(f"contact sheets in {args.sheets}")
    return 0


def contact_sheet(root: Path, group: Group, cell: int = 240) -> Image.Image:
    columns = min(len(group.photos), 6)
    rows = -(-len(group.photos) // columns)
    sheet = Image.new("RGB", (columns * cell, rows * (cell + 16)), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)
    for i, photo in enumerate(group.photos):
        x, y = (i % columns) * cell, (i // columns) * (cell + 16)
        try:
            thumb = load_image(photo.absolute(root), max_size=cell - 8)
            sheet.paste(thumb, (x + (cell - thumb.width) // 2, y + (cell - thumb.height) // 2))
        except ImageLoadError:
            pass
        draw.text((x + 4, y + cell), photo.name, fill=(220, 220, 220))
    return sheet


if __name__ == "__main__":
    sys.exit(main())
