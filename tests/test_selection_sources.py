from pathlib import Path, PureWindowsPath

import pytest

from printpicker.selection import Selection, SourceExistsError
from printpicker.selection.sources import source_name


@pytest.fixture
def sel(tmp_path):
    with Selection.create(tmp_path / "sel", "S") as s:
        yield s


def test_add_multiple_sources(sel, tmp_path):
    a = tmp_path / "ALPE DEVERO 2026"
    b = tmp_path / "Foto" / "2025"
    a.mkdir()
    b.mkdir(parents=True)
    sa = sel.add_source(a)
    sb = sel.add_source(b)
    assert [s.name for s in sel.sources()] == ["ALPE DEVERO 2026", "2025"]
    assert sel.source(sa.id).path == a.resolve()
    assert sa.is_available and sb.is_available


def test_duplicate_source_rejected(sel, tmp_path):
    sel.add_source(tmp_path)
    with pytest.raises(SourceExistsError):
        sel.add_source(tmp_path)


def test_missing_source_detected_and_relinked(sel, tmp_path):
    old = tmp_path / "E" / "Foto"
    old.mkdir(parents=True)
    src = sel.add_source(old)
    old.rename(tmp_path / "F")  # drive remounted elsewhere
    assert not sel.source(src.id).is_available

    new = tmp_path / "F"
    relinked = sel.relink_source(src.id, new)
    assert relinked.is_available
    assert relinked.name == "Foto"  # name is kept for file prefixes


def test_sources_persist(tmp_path):
    folder = tmp_path / "photos"
    folder.mkdir()
    with Selection.create(tmp_path, "P") as s:
        s.add_source(folder)
    with Selection.open(tmp_path / "P") as s:
        assert [x.path for x in s.sources()] == [folder.resolve()]


def test_source_name_for_drive_root():
    assert source_name(Path("/Volumes/CCCOMA_X64F")) == "CCCOMA_X64F"
    assert source_name(PureWindowsPath("E:\\")) == "E"
