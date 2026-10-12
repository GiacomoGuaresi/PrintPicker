import os

# Run Qt tests without opening windows.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from helpers import make_photo


@pytest.fixture
def photo(tmp_path):
    def factory(name="photo.jpg", **kwargs):
        return make_photo(tmp_path / name, **kwargs)

    return factory


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path_factory):
    """Keep QSettings (base folder, price list) away from the user's real configuration."""
    from PySide6.QtCore import QSettings

    path = tmp_path_factory.mktemp("settings")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(path))
    yield
