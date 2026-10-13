"""Take the README screenshots from the real app, using the sample photos.

    uv run python scripts/make_screenshots.py

Needs ``samples/`` (``scripts/make_samples.py``). Creates a few selections in a temporary
folder with throwaway settings, drives the app through them and saves the screens to
``docs/screenshots/`` and a short animated tour to ``docs/images/demo.gif`` (English
interface). Your settings are not touched.
"""

from __future__ import annotations

import io
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QBuffer, QItemSelectionModel, QModelIndex, QSettings, Qt
from PySide6.QtWidgets import QApplication, QWidget

from printpicker.selection import Selection
from printpicker.ui.app import create_application
from printpicker.ui.main_window import MainWindow
from printpicker.ui.session_screen import SessionScreen
from printpicker.ui.settings import AppSettings
from printpicker.ui.viewer import PhotoViewer

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"
OUT = ROOT / "docs" / "screenshots"
DEMO = ROOT / "docs" / "images" / "demo.gif"
DEMO_WIDTH = 960
WINDOW = (1200, 800)
WIDTH = 1600  # saved width in pixels

# selection name -> (sample folder, picked rows per group, in order); groups not listed
# are left unseen.
SELECTIONS = {
    "Mountains 2025": ("Mountains 2025", [[0], [0], [1], [0, 2], [0], [], [1], [0]]),
    "City trip": ("City trip 2025", [[1], [0], [0, 2], [], [0]]),
    "Summer prints": ("Seaside 2025", [[0], [0], [1]]),
}


def wait_until(condition: Callable[[], bool], timeout: float = 60) -> None:
    end = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > end:
            raise TimeoutError("the app did not get there in time")
        QApplication.processEvents()
        time.sleep(0.01)


def settle(seconds: float = 1.0) -> None:
    """Let background thumbnails arrive and the screen repaint."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.01)


def save(widget: QWidget, name: str) -> None:
    image = widget.grab().toImage()
    image = image.scaledToWidth(WIDTH, Qt.TransformationMode.SmoothTransformation)
    path = OUT / f"{name}.png"
    image.save(str(path))
    print(f"  {path.relative_to(ROOT)}")


def set_picks(session: SessionScreen, rows: list[int], current: int = 0) -> None:
    view = session.group_view
    view.clearSelection()
    for row in rows:
        view.toggle_row(row)
    view.selectionModel().setCurrentIndex(
        view.photo_model.index(current), QItemSelectionModel.SelectionFlag.NoUpdate
    )


def review(session: SessionScreen, sample: Path, picks: list[list[int]]) -> None:
    """Add ``sample`` as a source and pick ``picks`` group by group."""
    session.add_source(sample)
    wait_until(lambda: session.pages.currentWidget() is session.groups_page)
    for rows in picks:
        set_picks(session, rows)
        session.next_group()


def main() -> int:
    if not SAMPLES.is_dir():
        print("samples/ not found: run scripts/make_samples.py first", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="printpicker-shots-"))
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(work / "conf"))

    _app = create_application([sys.argv[0]])  # keep a reference while the script runs
    settings = AppSettings()
    settings.base_dir = work / "PrintPicker"
    settings.base_dir.mkdir()

    # Fill the selections, oldest first so the newest card comes first.
    for name, (folder, picks) in SELECTIONS.items():
        Selection.create(settings.base_dir, name).close()
        session = SessionScreen(settings.base_dir / name, settings)
        review(session, SAMPLES / folder, picks)
        session.close_selection()
        session.deleteLater()
        time.sleep(1.1)  # distinct "last change" times

    window = MainWindow(settings)
    window.menuBar().hide()  # native on macOS: not part of the window there
    window.resize(WINDOW[0], 520)
    window.show()
    start = window.start_screen
    start.refresh()
    hide_temp_folder(start, settings)
    start.cards.clearSelection()
    start.cards.setCurrentIndex(QModelIndex())
    settle(2)
    save(window, "start")
    window.resize(*WINDOW)

    # Group view: the 4-shot burst of the seaside, two of them picked.
    window.open_selection(settings.base_dir / "Summer prints")
    session = window.session
    wait_until(lambda: session.pages.currentWidget() is session.groups_page)
    burst = next(i for i, g in enumerate(session.groups) if len(g.photos) == 4)
    session.show_group(burst)
    set_picks(session, [0])
    settle(2)
    save(window, "group")

    # Full-screen preview of the same group, with its filmstrip.
    group_view = session.group_view
    viewer = PhotoViewer(
        group_view.photo_model.photos,
        session._paths_for,
        lambda p: session.loader.cached(p.rel_path),
        group_view.picked(),
        0,
        window,
        show_crop=False,
    )
    viewer.resize(*WINDOW)
    viewer.show()
    viewer.raise_()
    viewer.activateWindow()
    wait_until(lambda: viewer.full_image is not None)
    wait_until(lambda: viewer.picked_overlay.size() == viewer.view.viewport().size())
    viewer._show_controls()
    settle(1.5)
    viewer._show_controls()
    save(viewer, "preview")
    viewer.close()

    # 4:3 phone shots with the 10×15 crop preview.
    phone = next(
        i
        for i, g in enumerate(session.groups)
        if any(p.rel_path.endswith("IMG_1012.jpg") for p in g.photos)
    )
    session.show_group(phone)
    set_picks(session, [1], current=1)
    settle(2)
    save(window, "crop")

    record_demo(window, settings)
    window.close()
    return 0


def hide_temp_folder(start, settings: AppSettings) -> None:
    """Show the default location instead of the temporary folder."""
    start.location.setText(
        start.location.text().replace(str(settings.base_dir), "~/Documents/PrintPicker")
    )


class Recorder:
    """Frames of the animated tour: (image, how long it stays on screen)."""

    def __init__(self) -> None:
        self.frames: list[tuple[Image.Image, int]] = []

    def add(self, widget: QWidget, ms: int) -> None:
        settle(0.8)
        image = widget.grab().toImage()
        image = image.scaledToWidth(DEMO_WIDTH, Qt.TransformationMode.SmoothTransformation)
        buffer = QBuffer()
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        self.frames.append((Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGB"), ms))

    def save(self, path: Path) -> None:
        images = [img.quantize(colors=256, dither=Image.Dither.NONE) for img, _ in self.frames]
        images[0].save(
            path,
            save_all=True,
            append_images=images[1:],
            duration=[ms for _, ms in self.frames],
            loop=0,
            optimize=True,
        )
        print(f"  {path.relative_to(ROOT)}")


def record_demo(window: MainWindow, settings: AppSettings) -> None:
    """Home → a group → pick → preview → crop warning → done."""
    rec = Recorder()
    window.show_start()
    hide_temp_folder(window.start_screen, settings)
    window.start_screen.cards.setCurrentIndex(QModelIndex())
    rec.add(window, 2200)

    window.open_selection(settings.base_dir / "Summer prints")
    session = window.session
    wait_until(lambda: session.pages.currentWidget() is session.groups_page)
    burst = next(i for i, g in enumerate(session.groups) if len(g.photos) == 4)
    session.show_group(burst)
    set_picks(session, [])
    rec.add(window, 1600)
    set_picks(session, [0])
    rec.add(window, 1300)
    set_picks(session, [0, 3], current=3)
    rec.add(window, 1500)

    group_view = session.group_view
    viewer = PhotoViewer(
        group_view.photo_model.photos,
        session._paths_for,
        lambda p: session.loader.cached(p.rel_path),
        group_view.picked(),
        0,
        window,
        show_crop=False,
    )
    viewer.resize(*WINDOW)
    viewer.show()
    wait_until(lambda: viewer.full_image is not None)
    wait_until(lambda: viewer.picked_overlay.size() == viewer.view.viewport().size())
    viewer._show_controls()
    rec.add(viewer, 2000)
    viewer.close()

    set_picks(session, [0])
    session.next_group()
    phone = next(
        i
        for i, g in enumerate(session.groups)
        if any(p.rel_path.endswith("IMG_1012.jpg") for p in g.photos)
    )
    session.show_group(phone)
    set_picks(session, [1], current=1)
    rec.add(window, 1800)

    session.show_end()
    rec.add(window, 2600)
    session.close_selection()
    rec.save(DEMO)


if __name__ == "__main__":
    sys.exit(main())
