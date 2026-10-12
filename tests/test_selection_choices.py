import pytest

from printpicker.core.grouping import Group, group_photos
from printpicker.core.scanner import PhotoFile
from printpicker.selection import Selection
from printpicker.selection.choices import first_unseen_group

from helpers import make_photo


@pytest.fixture
def env(tmp_path):
    src = tmp_path / "src"
    make_photo(src / "a1.jpg", pattern=1)
    make_photo(src / "a2.jpg", pattern=1, color=(0, 0, 0))
    make_photo(src / "b.jpg", pattern=2)
    with Selection.create(tmp_path / "sels", "S") as sel:
        source = sel.add_source(src)
        groups = group_photos(sel.analyze_source(source), sel.threshold)
        yield sel, source, groups


def exported(sel):
    return sorted(p.name for p in sel.folder.iterdir() if not p.name.startswith("."))


def test_full_flow(env):
    sel, source, groups = env
    assert [len(g.photos) for g in groups] == [2, 1]
    assert first_unseen_group(groups, sel.seen_photos(source)) == 0

    sel.apply_choice(source, groups[0], {"a2.jpg"})
    assert sel.seen_photos(source) == {"a1.jpg", "a2.jpg"}
    assert sel.selected_photos(source) == {"a2.jpg"}
    assert exported(sel) == ["src - a2.jpg"]
    assert first_unseen_group(groups, sel.seen_photos(source)) == 1

    sel.apply_choice(source, groups[1], set())  # nothing picked
    assert first_unseen_group(groups, sel.seen_photos(source)) == 2
    assert sel.selected_count() == 1

    # Going back and changing the choice.
    sel.apply_choice(source, groups[0], {"a1.jpg", "a2.jpg"})
    assert exported(sel) == ["src - a1.jpg", "src - a2.jpg"]
    sel.apply_choice(source, groups[0], {"a1.jpg"})
    assert exported(sel) == ["src - a1.jpg"]
    assert sel.selected_count() == 1


def test_progress_survives_reopen_and_regrouping(env, tmp_path):
    sel, source, groups = env
    sel.apply_choice(source, groups[0], {"a1.jpg"})
    sel.threshold = 0
    sel.close()
    with Selection.open(tmp_path / "sels" / "S") as again:
        src = again.source(source.id)
        assert again.threshold == 0
        regrouped = group_photos(again.analyze_source(src), again.threshold)
        # With a different threshold the groups change, but choices are per photo.
        assert again.selected_photos(src) == {"a1.jpg"}
        idx = first_unseen_group(regrouped, again.seen_photos(src))
        assert regrouped[idx].photos[0].rel_path == "b.jpg"


def test_first_unseen_group_partial():
    groups = [Group("", (PhotoFile("a"), PhotoFile("b"))), Group("", (PhotoFile("c"),))]
    assert first_unseen_group(groups, {"a"}) == 0
    assert first_unseen_group(groups, {"a", "b", "c"}) == 2
    assert first_unseen_group([], set()) == 0


def test_failed_copy_leaves_group_unseen(env, monkeypatch):
    sel, source, groups = env
    from printpicker.selection import exports

    def boom(*_a, **_k):
        raise OSError("drive disconnected")

    monkeypatch.setattr(exports, "export_photo", boom)
    with pytest.raises(OSError):
        sel.apply_choice(source, groups[0], {"a1.jpg"})
    assert "a1.jpg" not in sel.seen_photos(source)
    assert first_unseen_group(groups, sel.seen_photos(source)) == 0
