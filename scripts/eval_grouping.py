"""Measure how well photos are grouped against the ground truth of the sample photos.

    uv run python scripts/eval_grouping.py [-v] [--folder NAME] [--method NAME] [--fresh]

Needs ``samples/`` with ``truth.json`` (``scripts/make_samples.py``). For each method, the
threshold is swept: the best one has the highest recall (fewest duplicates left for print)
with a precision of at least ``MIN_PRECISION`` (few unrelated photos in a group). Scores are
given for all folders and for the ``HARD`` ones, where the decision is taken. Features are
cached in ``samples/.cache/`` (``--fresh`` recomputes them, to measure the time per photo).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"
CACHE = SAMPLES / ".cache"
MIN_PRECISION = 0.9
# Folders that look like real shooting, where methods differ: the decision is taken on these.
HARD = ("Hard cases", "Work desk")

sys.path.insert(0, str(ROOT / "src"))

from printpicker.core.analysis import SIGNATURE_DECODE_SIZE, analyze_file  # noqa: E402
from printpicker.core.embedding import available  # noqa: E402
from printpicker.core.grouping import group_photos  # noqa: E402
from printpicker.core.hashing import phash  # noqa: E402
from printpicker.core.images import ImageLoadError, load_image  # noqa: E402
from printpicker.core.scanner import PhotoFile, scan  # noqa: E402
from printpicker.core.similarity import Signature, from_json, to_json  # noqa: E402

Pair = frozenset[str]


# --- Ground truth and metrics (pure, tested in tests/test_eval_grouping.py) ---------------


@dataclass
class Truth:
    """Labelled pairs of one folder, as file names."""

    same: set[Pair] = field(default_factory=set)
    apart: set[Pair] = field(default_factory=set)
    ideal_groups: int | None = None  # only for complete folders


def truth_from_json(entry: dict, names: Iterable[str]) -> Truth:
    """Labelled pairs of a folder of ``truth.json``; ``names`` are the photos found in it."""
    names = set(names)
    groups = [[n for n in g if n in names] for g in entry["groups"]]
    truth = Truth()
    group_of: dict[str, int] = {}
    for i, group in enumerate(groups):
        for name in group:
            group_of[name] = i
        truth.same.update(frozenset(p) for p in combinations(group, 2))
    truth.apart.update(frozenset(p) for p in entry.get("must_not", []) if set(p) <= names)
    if entry["complete"]:
        labelled = sorted(group_of)
        truth.apart.update(
            frozenset((a, b)) for a, b in combinations(labelled, 2) if group_of[a] != group_of[b]
        )
        truth.ideal_groups = sum(1 for g in groups if g)
    return truth


@dataclass
class Score:
    true_pos: int = 0  # same scene, grouped
    false_neg: int = 0  # same scene, split: a duplicate the user may print twice
    false_pos: int = 0  # different scenes, grouped
    true_neg: int = 0
    groups: int = 0
    ideal_groups: int = 0

    def __add__(self, other: Score) -> Score:
        return Score(
            *(a + b for a, b in zip(vars(self).values(), vars(other).values(), strict=True))
        )

    @property
    def precision(self) -> float:
        grouped = self.true_pos + self.false_pos
        return self.true_pos / grouped if grouped else 1.0

    @property
    def recall(self) -> float:
        same = self.true_pos + self.false_neg
        return self.true_pos / same if same else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0


def score(groups: Iterable[Iterable[str]], truth: Truth) -> Score:
    """Compare predicted groups (file names) with the labelled pairs; unlabelled pairs are
    ignored."""
    group_of = {name: i for i, group in enumerate(groups) for name in group}
    s = Score(groups=len(set(group_of.values())), ideal_groups=truth.ideal_groups or 0)
    for pair in truth.same:
        a, b = tuple(pair)
        if a in group_of and group_of[a] == group_of.get(b):
            s.true_pos += 1
        else:
            s.false_neg += 1
    for pair in truth.apart:
        a, b = tuple(pair)
        if a in group_of and group_of[a] == group_of.get(b):
            s.false_pos += 1
        else:
            s.true_neg += 1
    if truth.ideal_groups is None:
        s.groups = 0
    return s


def errors(groups: Iterable[Iterable[str]], truth: Truth) -> tuple[list[Pair], list[Pair]]:
    """The ``(split, merged)`` labelled pairs."""
    group_of = {name: i for i, group in enumerate(groups) for name in group}

    def together(pair: Pair) -> bool:
        a, b = tuple(pair)
        return a in group_of and group_of[a] == group_of.get(b)

    return (
        sorted((p for p in truth.same if not together(p)), key=sorted),
        sorted((p for p in truth.apart if together(p)), key=sorted),
    )


def best_threshold(scores: dict[float, Score]) -> float:
    """Highest recall with precision ≥ ``MIN_PRECISION`` (then highest F1, then strictest)."""
    ok = [t for t, s in scores.items() if s.precision >= MIN_PRECISION] or list(scores)
    return max(ok, key=lambda t: (round(scores[t].recall, 6), round(scores[t].f1, 6), -t))


# --- Methods ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Method:
    """A way of grouping: ``extract`` a feature per photo (JSON-friendly, cached under
    ``key``), then ``group`` with a threshold."""

    name: str
    key: str
    extract: Callable[[Path], object]
    group: Callable[[Sequence[tuple[PhotoFile, object]], float], list[list[str]]]
    thresholds: Sequence[float]


def _hash_only(path: Path) -> list | None:
    """The signature without embedding, as when the model is missing."""
    try:
        return to_json(Signature(phash(load_image(path, max_size=SIGNATURE_DECODE_SIZE))))
    except ImageLoadError:
        return None


def _app(path: Path) -> list | None:
    return to_json(analyze_file(path))


def _app_grouping(items: Sequence[tuple[PhotoFile, object]], threshold: float) -> list[list[str]]:
    groups = group_photos([(p, from_json(f)) for p, f in items], threshold)
    return [[p.name for p in g.photos] for g in groups]


_THRESHOLDS = [t / 2 for t in range(0, 61)]  # in hash bits, like the app's slider
METHODS = [
    Method("pHash only (no model)", "hash", _hash_only, _app_grouping, _THRESHOLDS),
    Method("app: pHash + DINOv2", "app", _app, _app_grouping, _THRESHOLDS),
]


# --- Running -----------------------------------------------------------------------------


def features(
    method: Method, photos: list[PhotoFile], fresh: bool = False
) -> tuple[dict[str, object], float]:
    """Feature of each photo (cached) and the extraction time per photo, in ms."""
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{method.key}.json"
    cache = json.loads(path.read_text()) if path.exists() and not fresh else {}
    elapsed, computed = 0.0, 0
    for photo in photos:
        file = photo.absolute(SAMPLES)
        key = f"{photo.rel_path}|{file.stat().st_size}|{file.stat().st_mtime_ns}"
        if key not in cache:
            started = time.perf_counter()
            cache[key] = method.extract(file)
            elapsed += time.perf_counter() - started
            computed += 1
        cache[photo.rel_path] = cache[key]
    path.write_text(json.dumps({k: v for k, v in cache.items() if "|" in k}))
    ms = 1000 * elapsed / computed if computed else float("nan")
    return {p.rel_path: cache[p.rel_path] for p in photos}, ms


def evaluate(
    method: Method,
    folders: dict[str, list[PhotoFile]],
    truths: dict[str, Truth],
    fresh: bool = False,
):
    """Scores per threshold and folder, and ms per photo."""
    all_photos = [p for photos in folders.values() for p in photos]
    feats, ms = features(method, all_photos, fresh)
    table: dict[float, dict[str, Score]] = {}
    for t in method.thresholds:
        table[t] = {}
        for folder, photos in folders.items():
            groups = method.group([(p, feats[p.rel_path]) for p in photos], t)
            table[t][folder] = score(groups, truths[folder])
    return table, ms


def line(label: str, s: Score) -> str:
    groups = f"groups {s.groups}/{s.ideal_groups}" if s.ideal_groups else ""
    return (
        f"{label:<22} P={s.precision:.2f} R={s.recall:.2f} F1={s.f1:.2f}  "
        f"split {s.false_neg:<3} merged {s.false_pos:<3} {groups}"
    )


def report(
    method: Method,
    table: dict[float, dict[str, Score]],
    ms: float,
    verbose: bool,
    detail: Callable[[float, str], tuple[list[Pair], list[Pair]]],
) -> float:
    totals = {t: sum(per.values(), Score()) for t, per in table.items()}
    best = best_threshold(totals)
    s = totals[best]
    good = [
        t for t, x in totals.items() if x.precision >= MIN_PRECISION and x.recall >= s.recall - 0.05
    ]
    hard = sum((x for f, x in table[best].items() if f in HARD), Score())
    timing = "cached" if math.isnan(ms) else f"{ms:.1f} ms/photo"
    print(f"{method.name}: threshold {best:g} (good {min(good):g}–{max(good):g}), {timing}")
    print("  " + line("all", s))
    print("  " + line("hard", hard))
    if verbose:
        for folder, x in table[best].items():
            print("    " + line(folder, x))
            split, merged = detail(best, folder)
            for kind, pairs in (("split", split), ("merged", merged)):
                for pair in pairs:
                    print(f"      {kind:<6} " + "  ".join(sorted(pair)))
    return best


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--folder", action="append", help="only these folders (repeatable)")
    parser.add_argument("--method", action="append", help="only these methods (hash, app)")
    parser.add_argument("--fresh", action="store_true", help="ignore the cache (for timings)")
    parser.add_argument("-v", "--verbose", action="store_true", help="scores per folder")
    args = parser.parse_args(argv)

    truth_path = SAMPLES / "truth.json"
    if not truth_path.exists():
        print("samples/truth.json not found: run scripts/make_samples.py", file=sys.stderr)
        return 1
    truth_json = json.loads(truth_path.read_text())
    folders: dict[str, list[PhotoFile]] = {}
    for photo in scan(SAMPLES):
        if photo.folder in truth_json and (not args.folder or photo.folder in args.folder):
            folders.setdefault(photo.folder, []).append(photo)
    truths = {
        f: truth_from_json(truth_json[f], (p.name for p in photos)) for f, photos in folders.items()
    }
    methods = [m for m in METHODS if not args.method or m.key in args.method]
    if any(m.key == "app" for m in methods) and not available():
        print("embedding model missing: run scripts/fetch_model.py", file=sys.stderr)
        return 1

    print(f"{sum(map(len, folders.values()))} photos, min precision {MIN_PRECISION}")
    for method in methods:
        table, ms = evaluate(method, folders, truths, args.fresh)

        def detail(t: float, folder: str, method: Method = method) -> tuple[list, list]:
            feats, _ = features(method, folders[folder])
            groups = method.group([(p, feats[p.rel_path]) for p in folders[folder]], t)
            return errors(groups, truths[folder])

        report(method, table, ms, args.verbose, detail)
    return 0


if __name__ == "__main__":
    sys.exit(main())
