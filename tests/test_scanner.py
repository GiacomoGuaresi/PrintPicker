from pathlib import Path

from printpicker.core.scanner import PhotoFile, natural_key, scan


def touch(root: Path, *rel: str) -> None:
    for r in rel:
        p = root / r
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"")


def test_scan_is_recursive_and_ordered(tmp_path):
    touch(
        tmp_path,
        "b.jpg",
        "a.JPG",
        "ALPE DEVERO 2026/img10.jpg",
        "ALPE DEVERO 2026/img2.jpg",
        "ALPE CAMAGGIORE 2026/x.heic",
        "ALPE CAMAGGIORE 2026/sub/y.cr2",
    )
    result = [p.rel_path for p in scan(tmp_path)]
    assert result == [
        "a.JPG",
        "b.jpg",
        "ALPE CAMAGGIORE 2026/x.heic",
        "ALPE CAMAGGIORE 2026/sub/y.cr2",
        "ALPE DEVERO 2026/img2.jpg",
        "ALPE DEVERO 2026/img10.jpg",
    ]


def test_scan_ignores_videos_hidden_and_system(tmp_path):
    touch(
        tmp_path,
        "clip.mp4",
        "movie.MOV",
        "notes.txt",
        ".hidden.jpg",
        ".Trashes/old.jpg",
        "System Volume Information/x.jpg",
        "$RECYCLE.BIN/y.jpg",
        "ok.png",
    )
    assert [p.rel_path for p in scan(tmp_path)] == ["ok.png"]


def test_scan_supports_all_formats(tmp_path):
    names = ["a.jpg", "b.jpeg", "c.png", "d.heic", "e.tif", "f.tiff", "g.webp", "h.nef", "i.dng"]
    touch(tmp_path, *names)
    assert sorted(p.rel_path for p in scan(tmp_path)) == names


def test_scan_missing_folder_yields_nothing(tmp_path):
    assert list(scan(tmp_path / "missing")) == []


def test_photo_file_properties(tmp_path):
    p = PhotoFile("2026/ALPE DEVERO/foto.jpg")
    assert p.folder == "2026/ALPE DEVERO"
    assert p.name == "foto.jpg"
    assert p.absolute(tmp_path) == tmp_path / "2026" / "ALPE DEVERO" / "foto.jpg"
    assert PhotoFile("root.jpg").folder == ""


def test_natural_key():
    names = ["img10.jpg", "IMG2.jpg", "img1.jpg"]
    assert sorted(names, key=natural_key) == ["img1.jpg", "IMG2.jpg", "img10.jpg"]
