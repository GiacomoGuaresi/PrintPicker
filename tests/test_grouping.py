import numpy as np
import pytest

from printpicker.core.grouping import PhotoIndex, group_photos
from printpicker.core.scanner import PhotoFile
from printpicker.core.similarity import EMBEDDING_PER_BIT, Signature, distance_matrix


def group(items, threshold):
    """Group ``(photo, hash)`` pairs: signatures without embedding, as without the model."""
    return group_photos([(p, None if h is None else Signature(h)) for p, h in items], threshold)


def vector(angle_bits):
    """Unit vector whose cosine distance from vector(0) is ``angle_bits`` hash bits."""
    cos = 1 - angle_bits * EMBEDDING_PER_BIT
    v = np.zeros(384, dtype=np.float32)
    v[0], v[1] = cos, np.sqrt(1 - cos**2)
    return v


def names(groups):
    return [[p.rel_path for p in g.photos] for g in groups]


def test_similar_photos_are_grouped():
    items = [
        (PhotoFile("a1.jpg"), 0b0000),
        (PhotoFile("a2.jpg"), 0b0001),
        (PhotoFile("b1.jpg"), 0xFFFF_FFFF),
        (PhotoFile("a3.jpg"), 0b0011),
    ]
    assert names(group(items, threshold=2)) == [
        ["a1.jpg", "a2.jpg", "a3.jpg"],
        ["b1.jpg"],
    ]


def test_threshold_zero_only_identical():
    items = [(PhotoFile("a.jpg"), 1), (PhotoFile("b.jpg"), 1), (PhotoFile("c.jpg"), 3)]
    assert names(group(items, threshold=0)) == [["a.jpg", "b.jpg"], ["c.jpg"]]


def test_never_groups_across_folders():
    items = [(PhotoFile("x/a.jpg"), 7), (PhotoFile("y/b.jpg"), 7)]
    groups = group(items, threshold=64)
    assert names(groups) == [["x/a.jpg"], ["y/b.jpg"]]
    assert [g.folder for g in groups] == ["x", "y"]


def test_unhashed_photos_are_alone():
    items = [(PhotoFile("a.jpg"), None), (PhotoFile("b.jpg"), None), (PhotoFile("c.jpg"), 0)]
    assert names(group(items, threshold=64)) == [["a.jpg"], ["b.jpg"], ["c.jpg"]]


def test_joins_closest_group():
    items = [
        (PhotoFile("a.jpg"), 0b0000_0000),
        (PhotoFile("b.jpg"), 0b1111_0000),
        (PhotoFile("c.jpg"), 0b1110_0000),  # 1 from b, 3 from a
    ]
    assert names(group(items, threshold=3)) == [["a.jpg"], ["b.jpg", "c.jpg"]]


def test_order_follows_scan_order():
    items = [(PhotoFile(f"{i}.jpg"), i * 0xFF) for i in range(5)]
    groups = group(items, threshold=0)
    assert names(groups) == [[f"{i}.jpg"] for i in range(5)]


def test_empty():
    assert group_photos([]) == []


def test_complete_linkage_prevents_chaining():
    # a-b and b-c are within the threshold, but a-c is not: c must not join a's group.
    items = [
        (PhotoFile("a.jpg"), 0b0000),
        (PhotoFile("b.jpg"), 0b0011),
        (PhotoFile("c.jpg"), 0b1111),
    ]
    assert names(group(items, threshold=2)) == [["a.jpg", "b.jpg"], ["c.jpg"]]


def test_embedding_groups_photos_whose_hashes_differ():
    # Same scene reframed: hashes 32 bits apart, embeddings 5 "bits" apart.
    items = [
        (PhotoFile("a.jpg"), Signature(0, vector(0))),
        (PhotoFile("b.jpg"), Signature(0xFFFF_FFFF, vector(5))),
    ]
    assert names(group_photos(items, threshold=14)) == [["a.jpg", "b.jpg"]]
    assert names(group_photos(items, threshold=4)) == [["a.jpg"], ["b.jpg"]]


def test_distance_is_the_closer_of_hash_and_embedding():
    sigs = [Signature(0, vector(0)), Signature(0b111, vector(20)), Signature(0xFF, None), None]
    d = distance_matrix(sigs)
    assert d[0, 1] == pytest.approx(3)  # hash closer
    assert d[0, 2] == 8  # no embedding: hash only
    assert np.isinf(d[0, 3]) and np.isinf(d[3, 3])  # unreadable

    sigs[1] = Signature(0xFFFF, vector(2))
    assert distance_matrix(sigs)[0, 1] == pytest.approx(2, abs=1e-3)  # embedding closer


def test_index_regroups_at_any_threshold():
    # Hashes 32 bits apart: only the embeddings, 3 "bits" apart in a row, group them.
    items = [
        (PhotoFile(f"{i}.jpg"), Signature(0xFFFF << (16 * i), vector(i * 3))) for i in range(4)
    ]
    index = PhotoIndex(items)
    assert [len(g.photos) for g in index.groups(0)] == [1, 1, 1, 1]
    assert [len(g.photos) for g in index.groups(3.01)] == [2, 2]
    assert [len(g.photos) for g in index.groups(9.01)] == [4]
