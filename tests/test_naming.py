import pytest

from printpicker.export.naming import MAX_NAME_BYTES, needs_conversion, output_name


@pytest.mark.parametrize(
    ("source", "rel", "expected"),
    [
        ("Foto", "2026/ALPE DEVERO/foto.jpg", "2026 - ALPE DEVERO - foto.jpg"),
        ("Foto 2026", "20260101_171918.jpg", "Foto 2026 - 20260101_171918.jpg"),
        ("X", "ALPE DEVERO 2026/a.PNG", "ALPE DEVERO 2026 - a.PNG"),
        ("X", "iphone/IMG_1.HEIC", "iphone - IMG_1.jpg"),
        ("X", "raw/DSC_1.NEF", "raw - DSC_1.jpg"),
        ("X", "a/b.tiff", "a - b.jpg"),
        ("X", "a/b.webp", "a - b.jpg"),
        ("X", "a/b.jpeg", "a - b.jpeg"),
        ("Mac: stuff", "x.jpg", "Mac_ stuff - x.jpg"),
        ("X", 'what?/a"b.jpg', "what_ - a_b.jpg"),
    ],
)
def test_output_name(source, rel, expected):
    assert output_name(source, rel) == expected


def test_needs_conversion():
    assert not needs_conversion("a.JPG")
    assert not needs_conversion("a.png")
    assert needs_conversion("a.heic")
    assert needs_conversion("a.cr2")


def test_long_names_are_truncated():
    rel = "/".join(["cartella molto lunga con accenti èèè"] * 20) + "/foto.jpg"
    name = output_name("X", rel)
    assert len(name.encode()) <= MAX_NAME_BYTES
    assert name.endswith(" - foto.jpg")
