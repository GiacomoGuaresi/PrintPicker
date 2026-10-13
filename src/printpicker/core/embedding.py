"""Image embeddings: shots of the same scene get close vectors, even when reframed, taken in
portrait instead of landscape, recoloured or with the subject moved.

The model is DINOv2 ViT-S/14 (``scripts/fetch_model.py``). Without it, or without
onnxruntime, :func:`embed` returns ``None`` and photos are grouped by perceptual hash only.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

import numpy as np
from PIL import Image

MODEL_PATH = (
    Path(__file__).resolve().parent.parent / "resources" / "models" / "dinov2-small-fp16.onnx"
)
EMBEDDING_SIZE = 384
_INPUT_SIDE = 224
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


@cache
def _session():
    """The ONNX Runtime session, or ``None`` if the model cannot be loaded."""
    if not MODEL_PATH.is_file():
        return None
    try:
        import onnxruntime as ort

        options = ort.SessionOptions()
        # Photos are analysed by several threads at once: one core each.
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        return ort.InferenceSession(str(MODEL_PATH), options, providers=["CPUExecutionProvider"])
    except Exception:
        return None


def available() -> bool:
    return _session() is not None


def embed(img: Image.Image) -> np.ndarray | None:
    """Unit-length embedding of an RGB image, or ``None`` if the model is not available.

    The whole frame is used (squeezed to a square, not cropped), so a reframed shot still
    shares most of its content with the original.
    """
    session = _session()
    if session is None:
        return None
    small = img.convert("RGB").resize((_INPUT_SIDE, _INPUT_SIDE), Image.Resampling.BICUBIC)
    pixels = (np.asarray(small, dtype=np.float32) / 255 - _MEAN) / _STD
    batch = pixels.transpose(2, 0, 1)[None]
    hidden = session.run(None, {"pixel_values": batch})[0]
    cls = hidden[0, 0].astype(np.float32)  # the image-level token
    return cls / np.linalg.norm(cls)


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """0 for identical directions, 1 for unrelated, 2 for opposite (unit vectors)."""
    return 1.0 - float(np.dot(a, b))
