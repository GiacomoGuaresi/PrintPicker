"""Formatting amounts of money for display."""

from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import QLocale

SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "CHF": "CHF"}


def format_money(amount: Decimal, currency: str = "EUR", locale: QLocale | None = None) -> str:
    locale = locale or QLocale()
    return locale.toCurrencyString(float(amount), SYMBOLS.get(currency, currency), 2)
