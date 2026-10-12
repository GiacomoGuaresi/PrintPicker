from printpicker.export.copy import copy_photo


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def test_copy_new(tmp_path):
    src = write(tmp_path / "src" / "a.jpg", b"AAA")
    dest = tmp_path / "dest"
    dest.mkdir()
    r = copy_photo(src, dest, "X - a.jpg")
    assert r.path == dest / "X - a.jpg" and not r.skipped
    assert r.path.read_bytes() == b"AAA"
    assert [p.name for p in dest.iterdir()] == ["X - a.jpg"]  # no temp file left


def test_identical_is_skipped(tmp_path):
    src = write(tmp_path / "a.jpg", b"AAA")
    dest = tmp_path / "dest"
    write(dest / "a.jpg", b"AAA")
    r = copy_photo(src, dest, "a.jpg")
    assert r.skipped and r.path == dest / "a.jpg"


def test_different_content_gets_suffix(tmp_path):
    dest = tmp_path / "dest"
    write(dest / "a.jpg", b"OLD")
    write(dest / "a_2.jpg", b"OLDER")
    r = copy_photo(write(tmp_path / "a.jpg", b"NEW"), dest, "a.jpg")
    assert r.path == dest / "a_3.jpg" and not r.skipped
    assert (dest / "a.jpg").read_bytes() == b"OLD"


def test_identical_to_suffixed_copy_is_skipped(tmp_path):
    dest = tmp_path / "dest"
    write(dest / "a.jpg", b"OLD")
    write(dest / "a_2.jpg", b"NEW")
    r = copy_photo(write(tmp_path / "a.jpg", b"NEW"), dest, "a.jpg")
    assert r.skipped and r.path == dest / "a_2.jpg"
