"""V3 — topic difficulty ladder + sibling lookup (ADR-0009)."""

from __future__ import annotations

from exam_engine.ladder import ladder_for, sibling


def test_ladder_for_returns_containing_list():
    assert ladder_for("ratio_medium") == ["ratio_easy", "ratio_medium", "ratio_hard"]


def test_ladder_for_unknown_is_none():
    assert ladder_for("nope") is None


def test_easy_has_no_easier_sibling():
    assert sibling("ratio_easy", -1) is None


def test_easy_harder_is_medium():
    assert sibling("ratio_easy", +1) == "ratio_medium"


def test_medium_has_both_siblings():
    assert sibling("ratio_medium", +1) == "ratio_hard"
    assert sibling("ratio_medium", -1) == "ratio_easy"


def test_hard_has_no_harder_sibling():
    assert sibling("ratio_hard", +1) is None


def test_unknown_code_has_no_sibling():
    assert sibling("does_not_exist", +1) is None
    assert sibling("does_not_exist", -1) is None
