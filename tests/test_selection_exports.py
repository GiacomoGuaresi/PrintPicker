import pytest

from printpicker.selection import Selection

from helpers import make_photo


@pytest.fixture
def env(tmp_path):
    src = tmp_path / "Foto 2026"
    make_photo(src / "a.jpg", pattern=1)
    make_photo(src / "DEVERO" / "b.jpg", pattern=2)
    with Selection.create(tmp_path / "sels", "S") as sel:
        yield sel, sel.add_source(src), src


def files(sel):
    return sorted(p.name for p in sel.folder.iterdir() if not p.name.startswith("."))


def test_export_and_unexport(env):
    sel, source, _ = env
    path = sel.export(source, "DEVERO/b.jpg")
    assert path == sel.folder / "DEVERO - b.jpg"
    sel.export(source, "a.jpg")
    assert files(sel) == ["DEVERO - b.jpg", "Foto 2026 - a.jpg"]
    assert sel.exported_count() == 2

    sel.unexport(source, "DEVERO/b.jpg")
    assert files(sel) == ["Foto 2026 - a.jpg"]
    assert sel.exported_name(source, "DEVERO/b.jpg") is None
    sel.unexport(source, "DEVERO/b.jpg")  # idempotent


def test_export_twice_is_noop(env):
    sel, source, _ = env
    assert sel.export(source, "a.jpg") == sel.export(source, "a.jpg")
    assert files(sel) == ["Foto 2026 - a.jpg"]


def test_shared_identical_file_is_kept(tmp_path):
    # Two sources containing the very same photo at the same relative path and source name.
    s1, s2 = tmp_path / "1" / "Foto", tmp_path / "2" / "Foto"
    make_photo(s1 / "a.jpg", pattern=1)
    make_photo(s2 / "a.jpg", pattern=1)
    with Selection.create(tmp_path, "S") as sel:
        a, b = sel.add_source(s1), sel.add_source(s2)
        assert sel.export(a, "a.jpg") == sel.export(b, "a.jpg")
        sel.unexport(a, "a.jpg")
        assert files(sel) == ["Foto - a.jpg"]
        sel.unexport(b, "a.jpg")
        assert files(sel) == []


def test_exports_survive_reopen(env, tmp_path):
    sel, source, _ = env
    sel.export(source, "a.jpg")
    sel.close()
    with Selection.open(tmp_path / "sels" / "S") as again:
        assert again.exported_name(again.source(source.id), "a.jpg") == "Foto 2026 - a.jpg"
