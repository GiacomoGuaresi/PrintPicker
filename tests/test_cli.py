from printpicker.cli import main

from helpers import make_photo


def test_cli_prints_groups_and_sheets(tmp_path, capsys):
    src = tmp_path / "src"
    make_photo(src / "a1.jpg", pattern=1)
    make_photo(src / "a2.jpg", pattern=1, color=(10, 10, 10))
    make_photo(src / "b.jpg", pattern=2)
    sheets = tmp_path / "sheets"
    cache = tmp_path / "cache.json"

    assert main([str(src), "--sheets", str(sheets), "--cache", str(cache)]) == 0
    out = capsys.readouterr().out
    assert "(2) a1.jpg, a2.jpg" in out
    assert "(1) b.jpg" in out
    assert list(sheets.glob("*.jpg"))
    assert cache.exists()

    # Second run reuses the cache.
    assert main([str(src), "--cache", str(cache)]) == 0


def test_cli_rejects_missing_folder(tmp_path):
    assert main([str(tmp_path / "nope")]) == 2
