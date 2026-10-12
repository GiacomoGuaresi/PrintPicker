from decimal import Decimal

from PySide6.QtCore import QLocale, QSettings

from printpicker.core.pricing import DEFAULT_PRICE_LIST, PriceList, PriceTier
from printpicker.ui.money import format_money
from printpicker.ui.settings import AppSettings


def test_price_list_default_and_roundtrip(tmp_path):
    s = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    assert s.price_list == DEFAULT_PRICE_LIST
    custom = PriceList("Other", (PriceTier(1, Decimal("0.5")),))
    s.price_list = custom
    assert s.price_list == custom


def test_corrupted_price_list_falls_back(tmp_path):
    q = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    q.setValue("pricing/price_list", "{not json")
    assert AppSettings(q).price_list == DEFAULT_PRICE_LIST


def test_format_money():
    it = QLocale(QLocale.Language.Italian, QLocale.Country.Italy)
    assert format_money(Decimal("10.2"), "EUR", it).replace("\xa0", " ") == "10,20 €"
    us = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
    assert format_money(Decimal("10.2"), "EUR", us) == "€10.20"
