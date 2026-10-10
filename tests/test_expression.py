"""T5 — the ``expression`` answer (schema 1.11.0): "in terms of π / n"."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest
from exam_engine import canonical
from exam_engine.canonical import CanonicalValidationError
from exam_engine.convert import answer_inline
from exam_engine.expression import (
    check_expression_consistency,
    evaluate,
    expressions_equal,
    to_latex,
)
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

SOURCED = Path(__file__).parent / "fixtures" / "sourced"
NAMES = ("pi", "algebra", "linear")


def _obj(name: str) -> dict:
    return json.loads((SOURCED / f"standin_expression_{name}.json").read_text("utf-8"))


def _ans(name: str) -> dict:
    return _obj(name)["question"]["parts"][0]["answer"]


@pytest.mark.parametrize("name", NAMES)
def test_fixture_loads_and_is_consistent(name):
    canonical.load(_obj(name))
    assert all(check_expression_consistency(_ans(name)).values())


def test_fixture_answers_are_independently_derived():
    # semicircle of radius r: perimeter = pi*r + 2r  (derived here, not from the answer)
    r = 42
    assert evaluate(_ans("pi")) == pytest.approx(math.pi * r + 2 * r)
    # 17 tickets at $n
    assert evaluate(_ans("algebra"), {"n": 3.5}) == pytest.approx(17 * 3.5)
    # 3 notebooks (n) + 4 pens (n - 2): sample several n instead of trusting the algebra
    for n in (2, 3.5, 10, 41.25):
        assert evaluate(_ans("linear"), {"n": n}) == pytest.approx(3 * n + 4 * (n - 2))


def test_latex_forms():
    assert to_latex(_ans("pi")) == r"\left(42\pi + 84\right)\ \text{m}"
    assert to_latex(_ans("algebra")) == r"\$17n"
    assert to_latex(_ans("linear")) == r"\$(7n - 8)"
    unit_less = {
        "type": "expression",
        "terms": [
            {"coefficient": 1, "symbol": "x", "power": 2},
            {"coefficient": -1, "symbol": "x"},
            {"coefficient": 0.5, "symbol": None},
        ],
    }
    assert to_latex(unit_less) == "x^{2} - x + 0.5"
    assert to_latex({"type": "expression", "terms": [{"coefficient": -1, "symbol": "n"}]}) == "-n"


@pytest.mark.parametrize("name", NAMES)
def test_key_prints_it_and_the_sheet_does_not(name):
    obj = canonical.load(_obj(name))
    key = render_answer_key_html("E", [obj])
    assert "Answer: \\(" in key and "final-answer" in key
    assert "Answer:" not in render_worksheet_html("E", [obj])


def test_convert_gives_a_math_node():
    node = answer_inline(_ans("pi"))
    assert node == [{"type": "math", "attrs": {"latex": to_latex(_ans("pi"))}}]


@pytest.mark.parametrize(
    ("mutate", "failing"),
    [
        (lambda a: a["terms"].append({"coefficient": 2, "symbol": "π"}), "like_terms_collected"),
        (lambda a: a["terms"].reverse(), "terms_in_canonical_order"),
        (lambda a: a["terms"][0].update(coefficient=0), "coefficients_finite_nonzero"),
        (lambda a: a["terms"][0].update(coefficient=1.23456), "coefficients_print_exactly"),
        (lambda a: a["terms"][1].update(power=2), "constant_has_no_power"),
    ],
)
def test_corruptions_are_caught_by_the_load_gate(mutate, failing):
    obj = _obj("pi")
    mutate(obj["question"]["parts"][0]["answer"])
    if validate_object(obj) == []:
        with pytest.raises(CanonicalValidationError) as exc:
            canonical.load(obj)
        assert f"expression inconsistent: {failing}" in str(exc.value)
    assert check_expression_consistency(obj["question"]["parts"][0]["answer"])[failing] is False


def test_schema_rejects_malformed_expressions():
    def bad(answer):
        obj = _obj("pi")
        obj["question"]["parts"][0]["answer"] = answer
        return validate_object(obj)

    term = {"coefficient": 1, "symbol": "n"}
    assert bad({"type": "expression", "terms": []}) != []
    assert bad({"type": "expression", "terms": [{"symbol": "n"}]}) != []
    assert bad({"type": "expression", "terms": [dict(term, symbol="nn")]}) != []
    assert bad({"type": "expression", "terms": [dict(term, power=0)]}) != []
    assert bad({"type": "expression", "terms": [dict(term, coefficient=10**400)]}) != []
    assert bad({"type": "expression", "terms": [term], "extra": 1}) != []
    assert bad({"type": "expression", "terms": [term]}) == []


def test_equality_is_exact_and_order_insensitive():
    a = _ans("pi")
    b = copy.deepcopy(a)
    b["terms"].reverse()
    assert expressions_equal(a, b)
    c = copy.deepcopy(a)
    c["terms"][1]["coefficient"] = 83
    assert not expressions_equal(a, c)
    split = {
        "type": "expression",
        "unit": "m",
        "terms": [
            {"coefficient": 40, "symbol": "π"},
            {"coefficient": 2, "symbol": "π"},
            {"coefficient": 84, "symbol": None},
        ],
    }
    assert expressions_equal(a, split)  # like terms collect
    assert not expressions_equal(a, dict(a, unit="cm"))
