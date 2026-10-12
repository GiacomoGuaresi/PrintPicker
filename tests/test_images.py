import pytest
from PIL import Image

from printpicker.core.images import ImageLoadError, load_image


def test_load_jpeg_rgb(photo):
    img = load_image(photo("a.jpg", size=(300, 200)))
    assert img.mode == "RGB"
    assert img.size == (300, 200)


def test_exif_orientation_is_applied(photo):
    # Orientation 6 = rotate 90° clockwise to display upright.
    img = load_image(photo("rot.jpg", size=(300, 200), orientation=6))
    assert img.size == (200, 300)


def test_max_size_fits_box(photo):
    img = load_image(photo("big.jpg", size=(2000, 1000)), max_size=256)
    assert max(img.size) == 256
    assert img.size == (256, 128)


def test_png_transparency_flattened_on_white(tmp_path):
    p = tmp_path / "t.png"
    Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(p)
    img = load_image(p)
    assert img.mode == "RGB"
    assert img.getpixel((0, 0)) == (255, 255, 255)


@pytest.mark.parametrize("ext", ["tiff", "webp", "png"])
def test_other_formats(tmp_path, ext):
    p = tmp_path / f"x.{ext}"
    Image.new("RGB", (40, 30), (1, 2, 3)).save(p)
    assert load_image(p).size == (40, 30)


def test_corrupt_file_raises(tmp_path):
    p = tmp_path / "bad.jpg"
    p.write_bytes(b"not an image")
    with pytest.raises(ImageLoadError):
        load_image(p)
