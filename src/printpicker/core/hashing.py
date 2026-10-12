"""Perceptual hashing: visually similar photos get hashes with a small Hamming distance."""

from __future__ import annotations

from functools import cache

import numpy as np
from PIL import Image

HASH_BITS = 64
_HASH_SIDE = 8  # 8 × 8 low-frequency DCT coefficients -> 64 bits
_SAMPLE_SIDE = 32  # image is reduced to 32 × 32 greyscale before the DCT


@cache
def _dct_matrix(n: int) -> np.ndarray:
    """Orthonormal DCT-II matrix: ``M @ x`` is the DCT of the column vector ``x``."""
    k = np.arange(n)[:, None]
    i = np.arange(n)[None, :]
    m = np.cos(np.pi * (2 * i + 1) * k / (2 * n)) * np.sqrt(2 / n)
    m[0] /= np.sqrt(2)
    return m


def phash(img: Image.Image) -> int:
    """64-bit perceptual hash (pHash) of an image.

    The image is reduced to 32 × 32 greyscale, transformed with a 2-D DCT, and each of the
    8 × 8 lowest frequencies becomes a bit: 1 if above the median of those frequencies.
    """
    small = img.convert("L").resize((_SAMPLE_SIDE, _SAMPLE_SIDE), Image.Resampling.LANCZOS)
    pixels = np.asarray(small, dtype=np.float64)
    m = _dct_matrix(_SAMPLE_SIDE)
    dct = m @ pixels @ m.T
    low = dct[:_HASH_SIDE, :_HASH_SIDE].flatten()
    # Median excluding the DC term, which only reflects overall brightness.
    bits = low > np.median(low[1:])
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


def hamming(a: int, b: int) -> int:
    """Number of differing bits between two hashes."""
    return (a ^ b).bit_count()
