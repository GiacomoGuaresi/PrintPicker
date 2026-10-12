from decimal import Decimal as D

import pytest

from printpicker.core.pricing import DEFAULT_PRICE_LIST, FixedCost, PriceList, PriceTier


@pytest.mark.parametrize(
    ("count", "unit", "total"),
    [
        (0, "0.35", "0"),
        (1, "0.35", "0.35"),
        (19, "0.35", "6.65"),
        (20, "0.30", "6.00"),
        (34, "0.30", "10.20"),
        (120, "0.25", "30.00"),
        (399, "0.19", "75.81"),
        (400, "0.16", "64.00"),
    ],
)
def test_photosi_estimate(count, unit, total):
    e = DEFAULT_PRICE_LIST.estimate(count)
    assert e.unit_price == D(unit)
    assert e.total == D(total)


def test_fixed_costs_added_only_when_ordering():
    pl = PriceList("x", (PriceTier(1, D("0.10")),), (FixedCost("Shipping", D("4.90")),))
    assert pl.estimate(10).total == D("5.90")
    assert pl.estimate(10).fixed == D("4.90")
    assert pl.estimate(0).total == 0


def test_tiers_are_sorted_and_validated():
    pl = PriceList("x", (PriceTier(10, D("0.2")), PriceTier(1, D("0.3"))))
    assert [t.min_quantity for t in pl.tiers] == [1, 10]
    with pytest.raises(ValueError):
        PriceList("x", (PriceTier(5, D("0.2")),))
    with pytest.raises(ValueError):
        PriceList("x", (PriceTier(1, D("0.2")), PriceTier(1, D("0.1"))))
    with pytest.raises(ValueError):
        PriceList("x", (PriceTier(1, D("-1")),))
    with pytest.raises(ValueError):
        PriceList("x", ())


def test_tier_ranges():
    assert DEFAULT_PRICE_LIST.tier_ranges()[:2] == [(1, 19, D("0.35")), (20, 99, D("0.30"))]
    assert DEFAULT_PRICE_LIST.tier_ranges()[-1] == (400, None, D("0.16"))


def test_roundtrip():
    pl = PriceList("x", (PriceTier(1, D("0.35")),), (FixedCost("Spedizione", D("5.90")),))
    assert PriceList.from_dict(pl.to_dict()) == pl
    assert PriceList.from_dict(DEFAULT_PRICE_LIST.to_dict()) == DEFAULT_PRICE_LIST
