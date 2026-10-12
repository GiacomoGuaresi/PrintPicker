import os

import pytest

from printpicker.core import analysis
from printpicker.selection import Selection
from printpicker.selection.photos import from_db_hash, to_db_hash

from helpers import make_photo


@pytest.fixture
def setup(tmp_path):
    src = tmp_path / "src"
    for i in range(4):
        make_photo(src / f"{i}.jpg", pattern=i)
    make_photo(src / "sub" / "x.jpg", pattern=9)
    (src / "bad.jpg").write_bytes(b"broken")
    with Selection.create(tmp_path, "S") as sel:
        yield sel, sel.add_source(src), src


@pytest.fixture
def count_hashing(monkeypatch):
    calls = []
    real = analysis.hash_file

    def counting(path):
        calls.append(path.name)
        return real(path)

    monkeypatch.setattr(analysis, "hash_file", counting)
    return calls


def test_hashes_are_cached(setup, count_hashing):
    sel, source, src = setup
    first = sel.analyze_source(source)
    assert [p.rel_path for p, _ in first] == [
        "0.jpg",
        "1.jpg",
        "2.jpg",
        "3.jpg",
        "bad.jpg",
        "sub/x.jpg",
    ]
    assert dict((p.rel_path, h) for p, h in first)["bad.jpg"] is None
    assert len(count_hashing) == 6

    count_hashing.clear()
    second = sel.analyze_source(source)
    assert second == first
    assert count_hashing == []  # nothing re-decoded, unreadable files included


def test_changed_and_new_files_are_rehashed(setup, count_hashing):
    sel, source, src = setup
    sel.analyze_source(source)
    count_hashing.clear()
    make_photo(src / "1.jpg", pattern=42)
    st = os.stat(src / "1.jpg")
    os.utime(src / "1.jpg", ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))
    make_photo(src / "new.jpg", pattern=7)
    sel.analyze_source(source)
    assert sorted(count_hashing) == ["1.jpg", "new.jpg"]


def test_progress_and_cancel(setup):
    sel, source, _ = setup
    seen = []
    result = sel.analyze_source(
        source, progress=lambda d, t: seen.append((d, t)), cancelled=lambda: len(seen) >= 3
    )
    assert seen[0] == (0, 6)
    assert len(result) < 6
    # Resuming continues from the cache.
    seen.clear()
    assert len(sel.analyze_source(source, progress=lambda d, t: seen.append((d, t)))) == 6
    assert seen[0][0] == len(result)


def test_cache_survives_reopen(setup, count_hashing, tmp_path):
    sel, source, _ = setup
    sel.analyze_source(source)
    sel.close()
    count_hashing.clear()
    with Selection.open(tmp_path / "S") as again:
        again.analyze_source(again.source(source.id))
    assert count_hashing == []


@pytest.mark.parametrize("h", [0, 1, 2**63 - 1, 2**63, 2**64 - 1, None])
def test_hash_roundtrip(h):
    assert from_db_hash(to_db_hash(h)) == h
