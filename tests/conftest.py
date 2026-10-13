import os

# Run Qt tests without opening windows.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from printpicker.core import embedding

from helpers import make_photo


@pytest.fixture
def model():
    """The embedding model. Skipped without it (scripts/fetch_model.py), unless CI says it must
    be there."""
    if not embedding.available():
        if os.environ.get("PRINTPICKER_REQUIRE_MODEL"):
            pytest.fail("embedding model missing: run scripts/fetch_model.py")
        pytest.skip("embedding model missing: run scripts/fetch_model.py")


@pytest.fixture(autouse=True)
def no_model_unless_asked(request, monkeypatch):
    """Group by hash only, as without the model, unless the test uses the ``model`` fixture:
    test photos are synthetic patterns, which the model finds all alike."""
    if "model" not in request.fixturenames:
        monkeypatch.setattr(embedding, "_session", lambda: None)


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
