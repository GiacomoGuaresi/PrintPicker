"""What photos are compared by, and how far apart two photos are."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from PIL import Image

from printpicker.core.embedding import EMBEDDING_SIZE, embed
from printpicker.core.hashing import phash

# Distances are in perceptual-hash bits, the unit of the similarity threshold. An embedding
# distance is converted so that the default threshold (14 bits) matches a cosine distance of
# 0.15, where shots of the same scene and different photos separate best on the sample
# photos (scripts/eval_grouping.py).
EMBEDDING_PER_BIT = 0.15 / 14


@dataclass(frozen=True, eq=False)
class Signature:
    """Perceptual hash and, when the model is available, embedding of a photo."""

    phash: int
    embedding: np.ndarray | None = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Signature):
            return NotImplemented
        if self.embedding is None or other.embedding is None:
            same_embedding = self.embedding is other.embedding
        else:
            same_embedding = np.array_equal(self.embedding, other.embedding)
        return self.phash == other.phash and same_embedding


def signature(img: Image.Image) -> Signature:
    return Signature(phash(img), embed(img))


def distance_matrix(signatures: Sequence[Signature | None]) -> np.ndarray:
    """Pairwise distances in hash bits (float32), ``inf`` for unreadable photos (``None``).

    Two photos are as close as the closer of the two measures: the hash recognises copies of
    the same photo (resized, in black and white), the embedding the same scene shot again
    (reframed, in portrait, with another light or the subject moved).
    """
    n = len(signatures)
    readable = np.array([s is not None for s in signatures], dtype=bool)
    hashes = np.array([s.phash if s is not None else 0 for s in signatures], dtype=np.uint64)
    dist = np.bitwise_count(hashes[:, None] ^ hashes[None, :]).astype(np.float32)

    embedded = np.array([s is not None and s.embedding is not None for s in signatures], dtype=bool)
    if embedded.any():
        vectors = np.zeros((n, EMBEDDING_SIZE), dtype=np.float32)
        vectors[embedded] = np.stack([signatures[i].embedding for i in np.flatnonzero(embedded)])
        cosine = (1 - vectors @ vectors.T) / EMBEDDING_PER_BIT
        both = embedded[:, None] & embedded[None, :]
        dist = np.where(both, np.minimum(dist, cosine), dist).astype(np.float32)

    dist[~readable, :] = np.inf
    dist[:, ~readable] = np.inf
    return dist


def to_json(sig: Signature | None) -> list | None:
    """JSON-friendly form of a signature (debug and benchmark caches)."""
    if sig is None:
        return None
    return [sig.phash, None if sig.embedding is None else sig.embedding.tolist()]


def from_json(value: list | None) -> Signature | None:
    if value is None:
        return None
    h, vector = value
    return Signature(h, None if vector is None else np.asarray(vector, dtype=np.float32))
