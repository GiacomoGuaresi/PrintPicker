import pytest

from helpers import make_photo


@pytest.fixture
def photo(tmp_path):
    def factory(name="photo.jpg", **kwargs):
        return make_photo(tmp_path / name, **kwargs)

    return factory
