"""Global application settings (stored with QSettings in the user's config folder)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings, QStandardPaths

from printpicker.about import APP_NAME
from printpicker.core.pricing import DEFAULT_PRICE_LIST, PriceList

DEFAULT_PHOTOS_PER_PAGE = 8


def default_base_dir() -> Path:
    documents = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    return Path(documents or Path.home()) / APP_NAME


class AppSettings:
    def __init__(self, settings: QSettings | None = None) -> None:
        self._s = settings or QSettings()

    @property
    def base_dir(self) -> Path:
        value = self._s.value("selections/base_dir")
        return Path(value) if value else default_base_dir()

    @base_dir.setter
    def base_dir(self, path: Path) -> None:
        self._s.setValue("selections/base_dir", str(path))

    @property
    def price_list(self) -> PriceList:
        value = self._s.value("pricing/price_list")
        if value:
            try:
                return PriceList.from_dict(json.loads(value))
            except (ValueError, KeyError, TypeError, ArithmeticError):
                pass  # corrupted or from an incompatible version: fall back to the default
        return DEFAULT_PRICE_LIST

    @price_list.setter
    def price_list(self, price_list: PriceList) -> None:
        self._s.setValue("pricing/price_list", json.dumps(price_list.to_dict()))

    @property
    def photos_per_page(self) -> int:
        value = self._s.value("pricing/photos_per_page", DEFAULT_PHOTOS_PER_PAGE, type=int)
        return max(1, int(value))

    @photos_per_page.setter
    def photos_per_page(self, count: int) -> None:
        self._s.setValue("pricing/photos_per_page", count)

    @property
    def window_geometry(self) -> QByteArray:
        value = self._s.value("window/geometry")
        return value if isinstance(value, QByteArray) else QByteArray()

    @window_geometry.setter
    def window_geometry(self, geometry: QByteArray) -> None:
        self._s.setValue("window/geometry", geometry)

    # Updates -----------------------------------------------------------------------------

    @property
    def auto_update_check(self) -> bool:
        return bool(self._s.value("updates/auto", True, type=bool))

    @auto_update_check.setter
    def auto_update_check(self, enabled: bool) -> None:
        self._s.setValue("updates/auto", enabled)

    @property
    def last_update_check(self) -> datetime | None:
        value = self._s.value("updates/last_check")
        try:
            return datetime.fromisoformat(value) if value else None
        except (TypeError, ValueError):
            return None

    @last_update_check.setter
    def last_update_check(self, when: datetime) -> None:
        self._s.setValue("updates/last_check", when.isoformat(timespec="seconds"))

    @property
    def skipped_version(self) -> str:
        return str(self._s.value("updates/skipped", "") or "")

    @skipped_version.setter
    def skipped_version(self, version: str) -> None:
        self._s.setValue("updates/skipped", version)
