import pytest

from printpicker.core.print_format import PRINT_10X15, needs_crop, print_area


@pytest.mark.parametrize(
    ("w", "h", "crop"),
    [
        (6000, 4000, False),  # 3:2 DSLR
        (4000, 6000, False),  # 3:2 portrait
        (4000, 3000, True),  # 4:3 phone
        (3000, 4000, True),
        (1920, 1080, True),  # 16:9
        (3000, 2010, False),  # within tolerance
        (0, 0, False),
    ],
)
def test_needs_crop(w, h, crop):
    assert needs_crop(w, h) is crop


def test_print_area_4_3_landscape_crops_top_and_bottom():
    x, y, w, h = print_area(4000, 3000)
    assert (x, w) == (0, 4000)
    assert h == pytest.approx(4000 / 1.5)
    assert y == pytest.approx((3000 - h) / 2)


def test_print_area_16_9_crops_sides():
    x, y, w, h = print_area(1920, 1080)
    assert (y, h) == (0, 1080)
    assert w == pytest.approx(1620)


def test_print_area_portrait():
    x, y, w, h = print_area(3000, 4000)
    assert (y, h) == (0, 4000)
    assert w == pytest.approx(4000 / 1.5)
    assert x == pytest.approx((3000 - w) / 2)


def test_format_aspect():
    assert PRINT_10X15.aspect == 1.5
