from printpicker.ui.thumbnails import ThumbnailLoader

from helpers import make_photo


def test_loads_and_creates_missing_thumbnail(qtbot, tmp_path):
    photo = make_photo(tmp_path / "a.jpg", size=(1200, 800), pattern=1)
    thumb = tmp_path / "thumbs" / "a.jpg"
    loader = ThumbnailLoader()
    with qtbot.waitSignal(loader.ready, timeout=5000) as blocker:
        assert loader.request("a", photo, thumb) is None
    key, image = blocker.args
    assert key == "a" and not image.isNull()
    assert max(image.width(), image.height()) == 512
    assert thumb.is_file()
    assert loader.request("a", photo, thumb) is not None  # now served from memory
    loader.shutdown()


def test_unreadable_photo_gives_null_image(qtbot, tmp_path):
    bad = tmp_path / "bad.jpg"
    bad.write_bytes(b"x")
    loader = ThumbnailLoader()
    with qtbot.waitSignal(loader.ready, timeout=5000) as blocker:
        loader.request("bad", bad, tmp_path / "t.jpg")
    assert blocker.args[1].isNull()
    loader.shutdown()


def test_reset_discards_stale_results(qtbot, tmp_path):
    photo = make_photo(tmp_path / "a.jpg", pattern=1)
    loader = ThumbnailLoader()
    received = []
    loader.ready.connect(lambda k, _i: received.append(k))
    loader.request("old", photo, tmp_path / "t1.jpg")
    loader.reset()
    loader.pool.waitForDone()
    qtbot.wait(50)
    assert received == []
    loader.shutdown()
