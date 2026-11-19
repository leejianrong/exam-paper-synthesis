"""EXA-155 — a multiple-choice answer in terms of π does not give itself away.

Reviewed once, independent of ``mcq``: every check reads the four options back from their
printed text and the right answer from the printed question (``test_invariants_circles``'s
stem reader), never from the engine's own parts.

The guessing trick it guards against: with options (3π + 24), 6π, (6π + 12) and (6π + 24),
the answer is the one that shares a part with all the others. Built as a 2 × 2 grid instead,
every π part and every number is in exactly two options, so no option stands out. And as for
every hooked blueprint (EXA-156), a pupil who always picks the first or the last option must
not score well above chance.
"""

from __future__ import annotations

import re
from collections import Counter
from fractions import Fraction

import pytest
from exam_engine.blueprints.registry import get_solver
from exam_engine.document import verify_snapshot
from exam_engine.expression import in_terms_of_pi
from exam_engine.mcq import to_mcq
from exam_engine.pipeline import generate
from test_invariants_circles import _terms_from_stem

CODES = ["circles_medium", "circles_hard"]
# "\(\left(6\pi + 24\right)\ \text{cm}\)" or "\(6\pi\ \text{cm}\)"
_NUM = r"(\d+(?:\.\d+)?)"
_OPTION = re.compile(
    rf"^\\\((?:\\left\()?{_NUM}\\pi(?: \+ {_NUM})?(?:\\right\))?\\ \\text\{{cm\}}\\\)$"
)


def _read(text: str) -> tuple[Fraction, Fraction]:
    m = _OPTION.match(text)
    assert m, text
    return Fraction(m[1]), Fraction(m[2] or 0)


def _pi_questions(code: str, n: int):
    """The first ``n`` questions of ``code`` asked in terms of π, with their seeds."""
    out, seed = [], 0
    while len(out) < n:
        seed += 1
        obj = generate(code, seed)
        if "Leave your answer in terms of π." in obj["question"]["parts"][0]["text"]:
            out.append((seed, obj))
    return out


def _options(m: dict) -> tuple[list[tuple[Fraction, Fraction]], int]:
    answer = m["question"]["parts"][0]["answer"]
    return [_read(o["text"]) for o in answer["options"]], int(answer["correct"])


def _assert_grid(where, options, correct, right) -> None:
    assert len(set(options)) == 4, (where, options)  # distinct
    assert options.count(right) == 1 and options[correct - 1] == right, (where, options)
    pis = Counter(a for a, _ in options)
    numbers = Counter(b for _, b in options)
    assert sorted(pis.values()) == [2, 2], (where, options)  # each π part in exactly 2
    assert sorted(numbers.values()) == [2, 2], (where, options)  # each number in exactly 2
    assert all(a > 0 and b >= 0 for a, b in options), (where, options)
    assert options == sorted(options), (where, options)  # by the π part, then the number


@pytest.mark.parametrize("code", CODES)
def test_pi_options_are_a_two_by_two_grid_and_the_answer_sits_evenly(code):
    positions = []
    for seed, obj in _pi_questions(code, 400):
        m = to_mcq(obj, seed)
        options, correct = _options(m)
        _assert_grid(
            (code, seed), options, correct, _terms_from_stem(obj["question"]["parts"][0]["text"])
        )
        positions.append(correct)
        # each wrong option names its slip; the one wrong in both parts names both
        desc = m["question"]["parts"][0]["marking_scheme"][0]["description"]
        for label in {1, 2, 3, 4} - {correct}:
            assert re.search(rf"\({label}\) \w", desc), (code, seed, desc)
        if seed <= 60:
            assert verify_snapshot(m) == [], (code, seed)
    share = {p: positions.count(p) / len(positions) for p in (1, 2, 3, 4)}
    assert share[1] <= 0.4 and share[4] <= 0.4, (code, share)
    assert min(share.values()) >= 0.05, (code, share)


def _pure_pi(obj: dict, code: str = "") -> dict:
    """``obj`` with its answer cut to its π part alone (and, with ``code``, another blueprint
    code, so no solver hook applies)."""
    part = obj["question"]["parts"][0]
    part["answer"] = in_terms_of_pi(Fraction(part["answer"]["terms"][0]["coefficient"]), 0, "cm")
    if code:
        obj["blueprint_code"] = code
    return obj


def _a_pi_question():
    return _pi_questions("circles_medium", 1)[0][1]


def test_a_pure_pi_answer_with_a_wrong_number_is_still_a_grid(monkeypatch):
    obj = _pure_pi(_a_pi_question())
    a = Fraction(obj["question"]["parts"][0]["answer"]["terms"][0]["coefficient"])
    monkeypatch.setattr(
        get_solver("circles_medium"),
        "distractors",
        lambda params, solution: [
            (in_terms_of_pi(a, 12, "cm"), "added the two radii"),
            (in_terms_of_pi(2 * a, 0, "cm"), "used the diameter as the radius"),
        ],
    )
    for seed in range(1, 41):
        options, correct = _options(to_mcq(obj, seed))
        _assert_grid(seed, options, correct, (a, Fraction(0)))
        assert {b for _, b in options} == {0, 12}, options


def test_a_pure_pi_answer_with_no_wrong_number_gets_four_pi_parts():
    obj = _pure_pi(_a_pi_question(), code="not_a_blueprint")
    a = Fraction(obj["question"]["parts"][0]["answer"]["terms"][0]["coefficient"])
    positions = set()
    for seed in range(1, 41):
        options, correct = _options(to_mcq(obj, seed))
        assert len(set(options)) == 4 and {b for _, b in options} == {0}, options
        assert options[correct - 1] == (a, 0) and options == sorted(options), options
        assert all(p > 0 for p, _ in options), options
        positions.add(correct)
    assert positions == {1, 2, 3, 4}


def test_unfair_slips_never_print(monkeypatch):
    """A slip equal to the answer, with no π part, a negative number or repeated is skipped:
    the grid still has four distinct, fair options."""
    obj = _a_pi_question()
    right = _terms_from_stem(obj["question"]["parts"][0]["text"])
    a, b = right
    monkeypatch.setattr(
        get_solver("circles_medium"),
        "distractors",
        lambda params, solution: [
            (in_terms_of_pi(a, b, "cm"), "the answer itself"),
            (in_terms_of_pi(0, b, "cm"), "no π part"),
            (in_terms_of_pi(a, -b, "cm"), "a negative number"),
            (in_terms_of_pi(a, b + 1, "cm"), "one more"),
            (in_terms_of_pi(a, b + 1, "cm"), "one more, again"),
        ],
    )
    for seed in range(1, 41):
        m = to_mcq(obj, seed)
        options, correct = _options(m)
        _assert_grid(seed, options, correct, right)
        desc = m["question"]["parts"][0]["marking_scheme"][0]["description"]
        for bad in ("the answer itself", "no π part", "a negative number", "again"):
            assert bad not in desc, desc


def test_a_constant_only_expression_is_not_offered_as_pi_multiple_choice():
    """Review of #235: an expression with no π part has nothing to build the grid from, so it
    is not convertible (it used to pass and then fail on an empty choice)."""
    from exam_engine.mcq import convertible

    obj = _a_pi_question()
    obj["question"]["parts"][0]["answer"] = in_terms_of_pi(0, 5, "cm")
    assert convertible(obj) is False
