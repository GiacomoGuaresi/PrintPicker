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


def test_convert_heic_to_jpeg(tmp_path):
    from PIL import Image

    from printpicker.export.copy import export_photo

    src = tmp_path / "IMG_1.HEIC"
    Image.new("RGB", (64, 48), (10, 120, 200)).save(src, format="HEIF")
    dest = tmp_path / "dest"
    dest.mkdir()
    r = export_photo(src, dest, "x - IMG_1.jpg")
    assert not r.skipped
    with Image.open(r.path) as out:
        assert out.format == "JPEG" and out.size == (64, 48)
    # Converting again produces the same output: skipped.
    assert export_photo(src, dest, "x - IMG_1.jpg").skipped
    assert sorted(p.name for p in dest.iterdir()) == ["x - IMG_1.jpg"]


def test_convert_bakes_orientation_and_keeps_icc(tmp_path):
    from PIL import Image, ImageCms

    from printpicker.export.copy import export_photo

    src = tmp_path / "a.tiff"
    exif = Image.Exif()
    exif[0x0112] = 6
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    Image.new("RGB", (60, 40), (1, 2, 3)).save(src, exif=exif, icc_profile=icc)
    dest = tmp_path / "d"
    dest.mkdir()
    r = export_photo(src, dest, "a.jpg")
    with Image.open(r.path) as out:
        assert out.size == (40, 60)
        assert out.info.get("icc_profile") == icc
        assert out.getexif().get(0x0112, 1) == 1


def test_export_jpeg_is_copied_unchanged(tmp_path):
    from printpicker.export.copy import export_photo

    from helpers import make_photo

    src = make_photo(tmp_path / "a.jpg", orientation=6)
    dest = tmp_path / "d"
    dest.mkdir()
    r = export_photo(src, dest, "a.jpg")
    assert r.path.read_bytes() == src.read_bytes()
