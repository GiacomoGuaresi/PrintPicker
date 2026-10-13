import datetime as dt
import sqlite3

import pytest

from printpicker.selection import (
    DATA_DIR,
    InvalidSelectionError,
    Selection,
    SelectionExistsError,
    default_selection_name,
    is_selection,
    list_selections,
    rename_selection,
    validate_name,
)
from printpicker.selection.schema import SCHEMA_VERSION, SchemaTooNewError


def test_create_and_reopen(tmp_path):
    with Selection.create(tmp_path, "Stampa Natale 2026") as sel:
        assert sel.folder == tmp_path / "Stampa Natale 2026"
        assert sel.name == "Stampa Natale 2026"
        assert (sel.folder / DATA_DIR / "selection.db").is_file()
        assert sel.thumbs_dir.is_dir()
        assert sel.get_meta("created_at")
        sel.set_meta("threshold", "14")
        sel.set_meta("threshold", "16")

    with Selection.open(tmp_path / "Stampa Natale 2026") as sel:
        assert sel.get_meta("threshold") == "16"
        assert sel.get_meta("missing", "x") == "x"
        version = sel.conn.execute("PRAGMA user_version").fetchone()[0]
        assert version == SCHEMA_VERSION


def test_create_existing_folder_fails(tmp_path):
    (tmp_path / "Taken").mkdir()
    with pytest.raises(SelectionExistsError):
        Selection.create(tmp_path, "Taken")


def test_open_non_selection_fails(tmp_path):
    with pytest.raises(InvalidSelectionError):
        Selection.open(tmp_path)


def test_list_selections(tmp_path):
    for name in ["Stampa 10", "Stampa 2"]:
        Selection.create(tmp_path, name).close()
    (tmp_path / "just a folder").mkdir()
    (tmp_path / "file.txt").write_text("x")
    assert [p.name for p in list_selections(tmp_path)] == ["Stampa 2", "Stampa 10"]
    assert is_selection(tmp_path / "Stampa 2")
    assert list_selections(tmp_path / "missing") == []


def test_default_name():
    assert default_selection_name(today=dt.date(2026, 10, 12)) == "Stampa 2026-10-12"
    assert default_selection_name("Print", dt.date(2026, 1, 2)) == "Print 2026-01-02"


@pytest.mark.parametrize(
    "bad", ["", "   ", "a/b", "a:b", 'q"', "x?", "end.", ".hidden", "CON", "com1.txt"]
)
def test_invalid_names(bad):
    with pytest.raises(InvalidSelectionError):
        validate_name(bad)


def test_valid_name_is_stripped():
    assert validate_name("  Stampa Natale  ") == "Stampa Natale"


def test_newer_schema_is_rejected(tmp_path):
    Selection.create(tmp_path, "S").close()
    db = tmp_path / "S" / DATA_DIR / "selection.db"
    conn = sqlite3.connect(db)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
    conn.close()
    with pytest.raises(SchemaTooNewError):
        Selection.open(tmp_path / "S")


def test_rename_selection(tmp_path):
    Selection.create(tmp_path, "Old").close()
    Selection.create(tmp_path, "Other").close()
    new = rename_selection(tmp_path / "Old", " New ")
    assert new == tmp_path / "New" and is_selection(new)
    assert not (tmp_path / "Old").exists()
    assert rename_selection(new, "new") == tmp_path / "new"  # case-only rename
    assert rename_selection(tmp_path / "new", "new") == tmp_path / "new"
    with pytest.raises(SelectionExistsError):
        rename_selection(tmp_path / "new", "Other")
    with pytest.raises(InvalidSelectionError):
        rename_selection(tmp_path / "new", "a/b")


def test_migrates_a_version_1_database():
    import sqlite3

    from printpicker.selection.schema import MIGRATIONS, migrate

    conn = sqlite3.connect(":memory:")
    conn.executescript(MIGRATIONS[0])
    conn.execute("PRAGMA user_version = 1")
    conn.execute("INSERT INTO sources (id, path, name, added_at) VALUES (1, '/x', 'X', 'now')")
    conn.execute("INSERT INTO photos (source_id, rel_path, hash, hashed) VALUES (1, 'a.jpg', 5, 1)")
    migrate(conn)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    row = conn.execute("SELECT hash, hashed, embedding FROM photos").fetchone()
    assert row == (5, 1, None)  # kept, embedding computed at the next analysis
