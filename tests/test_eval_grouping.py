import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parent.parent / "scripts" / "eval_grouping.py"
_spec = importlib.util.spec_from_file_location("eval_grouping", _PATH)
ev = importlib.util.module_from_spec(_spec)
sys.modules["eval_grouping"] = ev  # dataclasses look their module up
_spec.loader.exec_module(ev)


def pair(a, b):
    return frozenset((a, b))


def test_complete_truth_labels_every_pair():
    entry = {"complete": True, "groups": [["a", "b"], ["c"]]}
    truth = ev.truth_from_json(entry, ["a", "b", "c"])
    assert truth.same == {pair("a", "b")}
    assert truth.apart == {pair("a", "c"), pair("b", "c")}
    assert truth.ideal_groups == 2


def test_partial_truth_leaves_other_pairs_unlabelled():
    entry = {"complete": False, "groups": [["a", "b"]], "must_not": [["a", "c"]]}
    truth = ev.truth_from_json(entry, ["a", "b", "c", "d"])
    assert truth.same == {pair("a", "b")}
    assert truth.apart == {pair("a", "c")}
    assert truth.ideal_groups is None


def test_truth_ignores_missing_photos():
    entry = {"complete": True, "groups": [["a", "b", "x"]], "must_not": [["a", "y"]]}
    truth = ev.truth_from_json(entry, ["a", "b"])
    assert truth.same == {pair("a", "b")}
    assert truth.apart == set()


def test_score_counts_split_and_merged_pairs():
    truth = ev.truth_from_json({"complete": True, "groups": [["a", "b"], ["c"], ["d"]]}, "abcd")
    s = ev.score([["a"], ["b"], ["c", "d"]], truth)
    assert (s.true_pos, s.false_neg, s.false_pos) == (0, 1, 1)
    assert (s.groups, s.ideal_groups) == (3, 3)
    assert ev.errors([["a"], ["b"], ["c", "d"]], truth) == ([pair("a", "b")], [pair("c", "d")])


def test_score_precision_and_recall():
    truth = ev.truth_from_json({"complete": True, "groups": [["a", "b", "c"], ["d"]]}, "abcd")
    s = ev.score([["a", "b", "d"], ["c"]], truth)
    # same: ab ✓, ac ✗, bc ✗; apart: ad ✗ bd ✗ cd ✓
    assert s.precision == pytest.approx(1 / 3)
    assert s.recall == pytest.approx(1 / 3)
    assert (s + s).true_pos == 2


def test_best_threshold_prefers_recall_above_min_precision():
    scores = {
        1: ev.Score(true_pos=5, false_neg=5),  # P 1.0, R 0.5
        2: ev.Score(true_pos=9, false_neg=1, false_pos=1),  # P 0.9, R 0.9
        3: ev.Score(true_pos=10, false_pos=5),  # P 0.67, R 1.0
    }
    assert ev.best_threshold(scores) == 2
