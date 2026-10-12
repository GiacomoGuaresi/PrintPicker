from pathlib import Path

import pytest
from PIL import Image


def make_photo(
    path: Path,
    size: tuple[int, int] = (300, 200),
    color: tuple[int, int, int] = (200, 30, 30),
    orientation: int | None = None,
    pattern: int | None = None,
) -> Path:
    """Write a test photo. ``pattern`` draws seeded noise blocks so images differ visually."""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, color)
    if pattern is not None:
        import random

        rnd = random.Random(pattern)
        w, h = size
        block = max(1, min(w, h) // 8)
        for x in range(0, w, block):
            for y in range(0, h, block):
                c = tuple(rnd.randrange(256) for _ in range(3))
                img.paste(c, (x, y, x + block, y + block))
    kwargs = {}
    if orientation is not None:
        exif = Image.Exif()
        exif[0x0112] = orientation
        kwargs["exif"] = exif
    img.save(path, **kwargs)
    return path


@pytest.fixture
def photo(tmp_path):
    def factory(name="photo.jpg", **kwargs):
        return make_photo(tmp_path / name, **kwargs)

    return factory
