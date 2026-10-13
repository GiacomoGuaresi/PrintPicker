import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageEnhance

from printpicker.core import embedding
from printpicker.core.embedding import EMBEDDING_SIZE, cosine_distance, embed

_real_session = embedding._session  # tests run without the model unless they ask for it


def landscape() -> Image.Image:
    """Sky, sun and hills."""
    sky = Image.linear_gradient("L").resize((360, 240))
    img = Image.merge(
        "RGB",
        (
            sky.point(lambda v: 90 + v // 3),
            sky.point(lambda v: 140 + v // 3),
            Image.new("L", (360, 240), 235),
        ),
    )
    draw = ImageDraw.Draw(img)
    draw.ellipse((250, 30, 300, 80), fill=(255, 220, 80))
    hills = [(0, 240), (0, 150), (90, 70), (180, 160), (260, 100), (360, 170), (360, 240)]
    draw.polygon(hills, fill=(70, 110, 60))
    return img


def portrait() -> Image.Image:
    """A figure in front of a striped wall."""
    img = Image.new("RGB", (360, 240), (200, 60, 50))
    draw = ImageDraw.Draw(img)
    for x in range(0, 360, 40):
        draw.rectangle((x, 0, x + 18, 240), fill=(240, 230, 210))
    draw.ellipse((130, 40, 230, 140), fill=(30, 30, 30))
    draw.rectangle((150, 140, 210, 240), fill=(20, 40, 120))
    return img


def test_embedding_is_a_unit_vector(model):
    vector = embed(landscape())
    assert vector.shape == (EMBEDDING_SIZE,)
    assert np.linalg.norm(vector) == pytest.approx(1.0, abs=1e-5)


def test_reframed_shot_is_closer_than_another_scene(model):
    original = landscape()
    reframed = original.crop((30, 20, 360, 240)).resize(original.size)
    reframed = ImageEnhance.Brightness(reframed).enhance(0.8)
    same = cosine_distance(embed(original), embed(reframed))
    other = cosine_distance(embed(original), embed(portrait()))
    assert same < 0.1 < other


def test_without_model_there_is_no_embedding(monkeypatch, tmp_path):
    monkeypatch.setattr(embedding, "MODEL_PATH", tmp_path / "missing.onnx")
    monkeypatch.setattr(embedding, "_session", _real_session)
    _real_session.cache_clear()
    try:
        assert not embedding.available()
        assert embed(landscape()) is None
    finally:
        _real_session.cache_clear()


def test_cosine_distance():
    a, b = np.array([1.0, 0.0]), np.array([0.0, 1.0])
    assert cosine_distance(a, a) == pytest.approx(0.0)
    assert cosine_distance(a, b) == pytest.approx(1.0)
