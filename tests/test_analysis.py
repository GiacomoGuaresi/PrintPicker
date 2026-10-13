from printpicker.core.analysis import analyze_photos
from printpicker.core.scanner import scan

from helpers import make_photo


def test_analyze_photos_keeps_order_and_handles_bad_files(tmp_path):
    for i in range(6):
        make_photo(tmp_path / f"{i}.jpg", pattern=i)
    (tmp_path / "9_bad.jpg").write_bytes(b"broken")
    result = list(analyze_photos(tmp_path, scan(tmp_path), workers=3))
    assert [p.rel_path for p, _ in result] == [f"{i}.jpg" for i in range(6)] + ["9_bad.jpg"]
    assert all(h is not None for _, h in result[:-1])
    assert result[-1][1] is None


def test_closing_generator_cancels_pending_work(tmp_path, monkeypatch):
    from printpicker.core import analysis

    calls = []
    monkeypatch.setattr(analysis, "analyze_file", lambda path, thumb=None: calls.append(path) or 0)
    photos = [analysis.PhotoFile(f"{i}.jpg") for i in range(100)]
    gen = analyze_photos(tmp_path, photos, workers=2)
    next(gen)
    gen.close()
    assert len(calls) < 10
