# Contributing to PrintPicker

Thanks for your interest! PrintPicker is a small personal project, so the process is light.

## Reporting a problem

Use **Help → Report a problem…** in the app: it opens a GitHub issue with your version and system already filled in. Otherwise, [open a bug report](https://github.com/GiacomoGuaresi/PrintPicker/issues/new/choose) and paste the details from **Help → About PrintPicker → Copy**.

Please don't attach personal photos you don't want to make public.

## Suggesting an idea

[Open a feature request](https://github.com/GiacomoGuaresi/PrintPicker/issues/new/choose) describing the situation you're in. Points still being decided are listed in [docs/open-questions.md](docs/open-questions.md).

## Working on the code

Requirements: [uv](https://docs.astral.sh/uv/) (it installs the right Python by itself).

```sh
git clone https://github.com/GiacomoGuaresi/PrintPicker.git
cd PrintPicker
uv sync
uv run python scripts/fetch_model.py   # grouping model, ~44 MB (optional: without it, hash-only grouping)
uv run python -m printpicker           # run the app
uv run pytest                          # tests
uv run ruff check . && uv run ruff format .
```

Some ground rules:

- **Logic without Qt.** Scanning, hashing, grouping, selections, export and pricing live in `printpicker.core` and `printpicker.selection` and are tested without the UI.
- **Colours and icons come from the theme** (`src/printpicker/ui/theme.py`): no hard-coded colours in widgets (a test checks it).
- **Every interface text is translated**: English is the source, Italian lives in `scripts/update_translations.py`; run it after changing texts.
- **Small commits** with [Conventional Commits](https://www.conventionalcommits.org/) messages (`feat(ui): …`, `fix: …`, `docs: …`).

The specification and the development notes are in [`docs/`](docs/README.md) (in Italian): see [development](docs/development.md) for samples, benchmark, screenshots, icons and builds.

## Releases

Bump `__version__` in `src/printpicker/__init__.py`, then push a `vX.Y.Z` tag: GitHub Actions builds macOS, Windows and Linux and publishes the release. The app picks it up through its update check.
