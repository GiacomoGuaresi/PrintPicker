from printpicker.selection import DATA_DIR, Selection, summarize

from helpers import make_photo


def test_empty_selection(tmp_path):
    Selection.create(tmp_path, "S").close()
    summary = summarize(tmp_path / "S")
    assert summary.name == "S"
    assert (summary.photo_count, summary.source_count, summary.cover) == (0, 0, [])
    assert summary.last_used > 0


def test_counts_and_cover(tmp_path):
    src = tmp_path / "Foto"
    for i in range(6):
        make_photo(src / f"{i}.jpg", pattern=i)
    make_photo(tmp_path / "Altre" / "x.jpg", pattern=9)
    with Selection.create(tmp_path / "sels", "S") as sel:
        source = sel.add_source(src)
        sel.add_source(tmp_path / "Altre")
        for i in range(5):
            sel.export(source, f"{i}.jpg")
    summary = summarize(sel.folder)
    assert summary.photo_count == 5
    assert summary.source_count == 2
    assert [p.name for p, _ in summary.cover] == [f"Foto - {i}.jpg" for i in range(4)]
    assert summary.cover[0][1] == sel.thumb_path(source, "0.jpg")


def test_identical_photos_count_once(tmp_path):
    src = tmp_path / "Foto"
    make_photo(src / "a.jpg", pattern=1)
    with Selection.create(tmp_path / "sels", "S") as sel:
        source = sel.add_source(src)
        sel.export(source, "a.jpg")
        sel.conn.execute(
            "INSERT INTO photos (source_id, rel_path, exported_name) VALUES (?, 'b.jpg', ?)",
            (source.id, "Foto - a.jpg"),
        )
        sel.conn.commit()
    assert summarize(sel.folder).photo_count == 1


def test_unreadable_selection(tmp_path):
    Selection.create(tmp_path, "S").close()
    (tmp_path / "S" / DATA_DIR / "selection.db").write_bytes(b"not a database" * 100)
    summary = summarize(tmp_path / "S")
    assert summary.photo_count == 0
    assert summary.cover == []
