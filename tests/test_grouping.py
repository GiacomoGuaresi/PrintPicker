from printpicker.core.grouping import group_photos
from printpicker.core.scanner import PhotoFile


def names(groups):
    return [[p.rel_path for p in g.photos] for g in groups]


def test_similar_photos_are_grouped():
    items = [
        (PhotoFile("a1.jpg"), 0b0000),
        (PhotoFile("a2.jpg"), 0b0001),
        (PhotoFile("b1.jpg"), 0xFFFF_FFFF),
        (PhotoFile("a3.jpg"), 0b0011),
    ]
    assert names(group_photos(items, threshold=2)) == [
        ["a1.jpg", "a2.jpg", "a3.jpg"],
        ["b1.jpg"],
    ]


def test_threshold_zero_only_identical():
    items = [(PhotoFile("a.jpg"), 1), (PhotoFile("b.jpg"), 1), (PhotoFile("c.jpg"), 3)]
    assert names(group_photos(items, threshold=0)) == [["a.jpg", "b.jpg"], ["c.jpg"]]


def test_never_groups_across_folders():
    items = [(PhotoFile("x/a.jpg"), 7), (PhotoFile("y/b.jpg"), 7)]
    groups = group_photos(items, threshold=64)
    assert names(groups) == [["x/a.jpg"], ["y/b.jpg"]]
    assert [g.folder for g in groups] == ["x", "y"]


def test_unhashed_photos_are_alone():
    items = [(PhotoFile("a.jpg"), None), (PhotoFile("b.jpg"), None), (PhotoFile("c.jpg"), 0)]
    assert names(group_photos(items, threshold=64)) == [["a.jpg"], ["b.jpg"], ["c.jpg"]]


def test_joins_closest_group():
    items = [
        (PhotoFile("a.jpg"), 0b0000_0000),
        (PhotoFile("b.jpg"), 0b1111_0000),
        (PhotoFile("c.jpg"), 0b1110_0000),  # 1 from b, 3 from a
    ]
    assert names(group_photos(items, threshold=3)) == [["a.jpg"], ["b.jpg", "c.jpg"]]


def test_order_follows_scan_order():
    items = [(PhotoFile(f"{i}.jpg"), i * 0xFF) for i in range(5)]
    groups = group_photos(items, threshold=0)
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
    assert names(group_photos(items, threshold=2)) == [["a.jpg", "b.jpg"], ["c.jpg"]]
