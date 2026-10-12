"""RAW decoding, with LibRaw replaced by a fake (no sample RAW files in the repo)."""

import io
from types import SimpleNamespace

import numpy as np
import pytest
import rawpy
from PIL import Image

from printpicker.core import raw as raw_module
from printpicker.core.images import ImageLoadError, load_image


class FakeRaw:
    def __init__(self, thumb=None, flip=0, developed=(40, 60)):
        self._thumb = thumb
        self.sizes = SimpleNamespace(flip=flip)
        self._developed = developed
        self.postprocess_calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_thumb(self):
        if self._thumb is None:
            raise rawpy.LibRawNoThumbnailError()
        return self._thumb

    def postprocess(self, **kwargs):
        self.postprocess_calls.append(kwargs)
        h, w = self._developed
        return np.zeros((h, w, 3), dtype=np.uint8)


def jpeg_thumb(size):
    buf = io.BytesIO()
    Image.new("RGB", size, (9, 9, 9)).save(buf, format="JPEG")
    return SimpleNamespace(format=rawpy.ThumbFormat.JPEG, data=buf.getvalue())


@pytest.fixture
def fake(monkeypatch, tmp_path):
    def install(fake_raw):
        monkeypatch.setattr(raw_module.rawpy, "imread", lambda _p: fake_raw)
        path = tmp_path / "x.nef"
        path.write_bytes(b"raw")
        return path

    return install


def test_preview_uses_embedded_jpeg_with_flip(fake):
    fr = FakeRaw(thumb=jpeg_thumb((600, 400)), flip=6)
    img = load_image(fake(fr), max_size=300)
    assert img.size == (200, 300)  # rotated to portrait, then fitted
    assert fr.postprocess_calls == []


def test_preview_too_small_falls_back_to_develop(fake):
    fr = FakeRaw(thumb=jpeg_thumb((160, 120)))
    load_image(fake(fr), max_size=1000)
    assert fr.postprocess_calls and fr.postprocess_calls[0]["half_size"] is True


def test_full_size_always_develops(fake):
    fr = FakeRaw(thumb=jpeg_thumb((600, 400)), developed=(400, 600))
    img = load_image(fake(fr))
    assert img.size == (600, 400)
    assert fr.postprocess_calls[0]["half_size"] is False


def test_raw_error_becomes_image_load_error(monkeypatch, tmp_path):
    def boom(_p):
        raise rawpy.LibRawFileUnsupportedError()

    monkeypatch.setattr(raw_module.rawpy, "imread", boom)
    p = tmp_path / "bad.cr2"
    p.write_bytes(b"x")
    with pytest.raises(ImageLoadError):
        load_image(p)
