import os

import numpy as np
import pytest

from printpicker.core import analysis, embedding
from printpicker.selection import Selection
from printpicker.selection.photos import (
    from_db_embedding,
    from_db_hash,
    to_db_embedding,
    to_db_hash,
)

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
    real = analysis.analyze_file

    def counting(path, thumb_path=None):
        calls.append(path.name)
        return real(path, thumb_path)

    monkeypatch.setattr(analysis, "analyze_file", counting)
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


def test_embedding_roundtrip():
    v = np.linspace(-1, 1, 384, dtype=np.float32)
    assert np.allclose(from_db_embedding(to_db_embedding(v)), v, atol=1e-3)
    assert from_db_embedding(to_db_embedding(None)) is None


def test_embeddings_are_cached(setup, count_hashing, model):
    sel, source, _ = setup
    first = dict(sel.analyze_source(source))
    assert all(sig.embedding is not None for sig in first.values() if sig is not None)
    count_hashing.clear()
    second = dict(sel.analyze_source(source))
    assert count_hashing == []
    for photo, sig in first.items():
        if sig is None:
            assert second[photo] is None
        else:
            assert second[photo].phash == sig.phash
            assert np.allclose(second[photo].embedding, sig.embedding, atol=1e-3)


def test_photos_analysed_without_model_get_embeddings_later(
    setup, count_hashing, model, monkeypatch
):
    sel, source, _ = setup
    real_session = embedding._session
    monkeypatch.setattr(embedding, "_session", lambda: None)
    assert all(sig is None or sig.embedding is None for _, sig in sel.analyze_source(source))
    count_hashing.clear()

    monkeypatch.setattr(embedding, "_session", real_session)
    result = sel.analyze_source(source)
    assert sorted(count_hashing) == ["0.jpg", "1.jpg", "2.jpg", "3.jpg", "x.jpg"]  # not bad.jpg
    assert all(sig is None or sig.embedding is not None for _, sig in result)


def test_thumbnails_are_saved_during_analysis(setup):
    from PIL import Image

    sel, source, _ = setup
    sel.analyze_source(source)
    thumb = sel.thumb_path(source, "sub/x.jpg")
    assert thumb.is_file()
    with Image.open(thumb) as img:
        assert max(img.size) <= 512
    assert not sel.thumb_path(source, "bad.jpg").exists()


def test_disconnected_drive_is_not_cached_as_unreadable(setup, monkeypatch, tmp_path):
    from printpicker.selection.photos import SourceUnavailableError

    sel, source, src = setup
    real = analysis.analyze_file
    moved = tmp_path / "unplugged"

    import threading

    lock = threading.Lock()

    def unplug_after_first(path, thumb_path=None):
        with lock:  # hashing runs on several threads
            if not moved.exists():
                h = real(path, thumb_path)
                src.rename(moved)  # the drive goes away
                return h
        return None

    monkeypatch.setattr(analysis, "analyze_file", unplug_after_first)
    with pytest.raises(SourceUnavailableError):
        sel.analyze_source(source)
    rows = sel.conn.execute("SELECT COUNT(*) FROM photos WHERE hashed = 1").fetchone()[0]
    assert rows <= 1  # only the photo read before unplugging

    moved.rename(src)
    monkeypatch.setattr(analysis, "analyze_file", real)
    result = dict((p.rel_path, h) for p, h in sel.analyze_source(source))
    assert all(h is not None for rel, h in result.items() if rel != "bad.jpg")
