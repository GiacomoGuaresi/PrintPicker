from decimal import Decimal

from PySide6.QtCore import QLocale, QSettings

from printpicker.core.pricing import DEFAULT_PRICE_LIST, PriceList, PriceTier
from printpicker.ui import theme
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


def test_settings_dialog_changes_base_dir(qtbot, tmp_path):
    from printpicker.ui.settings_dialog import SettingsDialog

    s = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    dialog = SettingsDialog(s)
    qtbot.addWidget(dialog)
    dialog.base_dir_edit.setText(str(tmp_path / "Stampe"))
    dialog.accept()
    assert s.base_dir == tmp_path / "Stampe"


def make_dialog(qtbot, tmp_path):
    from printpicker.ui.settings_dialog import SettingsDialog

    s = AppSettings(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    dialog = SettingsDialog(s)
    qtbot.addWidget(dialog)
    return s, dialog


def test_price_editor_loads_default_and_saves_changes(qtbot, tmp_path):
    from PySide6.QtWidgets import QTableWidgetItem

    s, dialog = make_dialog(qtbot, tmp_path)
    assert dialog.tiers_table.rowCount() == 5
    assert dialog.price_list() == DEFAULT_PRICE_LIST
    dialog.tiers_table.item(1, 1).setText("0,28")
    dialog._add_row(dialog.fixed_table, "Spedizione", "")
    dialog.fixed_table.setItem(0, 1, QTableWidgetItem("4,90 €"))
    dialog.price_name.setText("PhotoSì promo")
    dialog.accept()
    saved = s.price_list
    assert saved.name == "PhotoSì promo"
    assert saved.unit_price(50) == Decimal("0.28")
    assert saved.estimate(50).total == Decimal("18.90")


def test_invalid_price_list_is_rejected(qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    s, dialog = make_dialog(qtbot, tmp_path)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a))
    dialog.tiers_table.item(0, 0).setText("5")  # no tier from 1 photo
    assert f"color:{theme.DANGER.name()}" in dialog.examples.text()
    dialog.accept()
    assert warnings
    assert s.price_list == DEFAULT_PRICE_LIST


def test_parse_decimal():
    import pytest

    from printpicker.ui.settings_dialog import parse_decimal

    assert parse_decimal("0,35") == Decimal("0.35")
    assert parse_decimal(" 4.90 € ") == Decimal("4.90")
    with pytest.raises(ValueError):
        parse_decimal("abc")


def test_photos_per_page_default_and_saved(qtbot, tmp_path):
    s, dialog = make_dialog(qtbot, tmp_path)
    assert s.photos_per_page == 8
    assert dialog.photos_per_page.value() == 8
    dialog.photos_per_page.setValue(12)
    dialog.accept()
    assert s.photos_per_page == 12
