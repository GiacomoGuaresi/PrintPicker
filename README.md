# PrintPicker

**Pick the best shots from your photo archive and get them ready for print — fast.**

PrintPicker is a small cross-platform desktop utility for people who keep their photos on an external drive, organized in folders. Point it at a folder, and it walks you through groups of visually similar photos one at a time: pick the ones you want, and they're copied into a print-ready folder on your computer, with a running estimate of what the print order will cost.

> **Status:** early design. The specification is being written in [`docs/`](docs/README.md); no code has been released yet.

## Features (planned)

- **Similar-photo groups** — photos are grouped by visual similarity (perceptual hashing), so bursts and near-duplicates are shown side by side and you pick the best one(s).
- **Fast keyboard-driven review** — arrows to move, Space to select, Enter to confirm and move on, Backspace to go back. Ctrl/Cmd+click for multiple picks.
- **Live similarity threshold** — a slider regroups photos on the fly, from strict to loose.
- **Full-screen preview** with 100% zoom to check focus and closed eyes.
- **Print selections** — each selection is a self-contained folder: the chosen photos plus a hidden `.printpicker/` folder with its database and thumbnails. Delete the folder after printing and nothing is left behind.
- **Resume anytime** — reopen a selection and continue from the first group you haven't seen.
- **Multiple sources per selection**, with graceful handling of disconnected or remapped drives.
- **Print-ready output** — flat folder, file names prefixed with their source path, HEIC/RAW/TIFF/WebP converted to JPG.
- **Cost estimate** — configurable tiered price list (PhotoSì 10×15 prices by default) with a live total.
- **Never touches your archive** — read-only on the source, always.

## Supported formats

JPG, PNG, HEIC, RAW (CR2, NEF, ARW, DNG, …), TIFF, WebP. Videos are ignored.

## Platforms

macOS, Windows and Linux.

## Tech stack

Python + Qt ([PySide6](https://doc.qt.io/qtforpython-6/)), [Pillow](https://python-pillow.org/), [imagehash](https://github.com/JohannesBuchner/imagehash), [pillow-heif](https://github.com/bigcat88/pillow_heif), [rawpy](https://github.com/letmaik/rawpy). Packaged with PyInstaller.

## Documentation

The full specification (in Italian) lives in [`docs/`](docs/README.md):

- [Overview](docs/overview.md)
- [Print selections](docs/selections.md)
- [Similar-photo grouping workflow](docs/grouping-workflow.md)
- [Copy and export](docs/export.md)
- [Print cost estimate](docs/cost-estimate.md)
- [Architecture](docs/architecture.md)
- [Development and testing](docs/development.md)
- [Open questions](docs/open-questions.md)

## Contributing

Issues and suggestions are welcome. The project is at the design stage, so the best way to help right now is to comment on the [open questions](docs/open-questions.md).

## License

[MIT](LICENSE) © 2026 Giacomo Guaresi
