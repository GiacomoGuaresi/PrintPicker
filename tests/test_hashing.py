from PIL import Image, ImageEnhance, ImageFilter

from printpicker.core.hashing import HASH_BITS, hamming, phash
from printpicker.core.images import load_image

from helpers import make_photo


def scene(tmp_path, name, seed, size=(400, 300)):
    return load_image(make_photo(tmp_path / name, size=size, pattern=seed))


def test_hash_is_64_bit_int(tmp_path):
    h = phash(scene(tmp_path, "a.jpg", 1))
    assert isinstance(h, int)
    assert 0 <= h < 2**HASH_BITS


def test_hash_is_deterministic(tmp_path):
    img = scene(tmp_path, "a.jpg", 1)
    assert phash(img) == phash(img.copy())


def test_similar_images_are_close(tmp_path):
    img = scene(tmp_path, "a.jpg", 1)
    variants = [
        img.resize((200, 150)),
        ImageEnhance.Brightness(img).enhance(1.15),
        img.filter(ImageFilter.GaussianBlur(1)),
    ]
    for v in variants:
        assert hamming(phash(img), phash(v)) <= 8


def test_different_images_are_far(tmp_path):
    a = phash(scene(tmp_path, "a.jpg", 1))
    b = phash(scene(tmp_path, "b.jpg", 2))
    assert hamming(a, b) > 16


def test_hamming():
    assert hamming(0b1011, 0b0001) == 2
    assert hamming(5, 5) == 0


def test_flat_image_does_not_crash():
    phash(Image.new("RGB", (50, 50), (128, 128, 128)))
