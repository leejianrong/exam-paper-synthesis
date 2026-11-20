"""EXA-89 — set-numbers: a teacher changes a generated question's free numbers.

The edit re-solves through ``pipeline.build_from_params``, so the correctness authority is
the same as for generation: after an accepted edit, each blueprint's own independent
invariant (from its ``test_invariants_*`` module) must hold for the new numbers, the
snapshot must verify, and the wording check must find nothing. Random numbers that don't
make a question are refused with the solver's own sentence, never the generic fallback
(which would mean ``number_problem`` misses a case ``validate`` catches).
"""

from __future__ import annotations

import copy

import pytest
import test_invariants_average as average_inv
import test_invariants_fractions as fractions_inv
import test_invariants_percentage as percentage_inv
import test_invariants_ratio as ratio_inv
import test_invariants_speed as speed_inv
from exam_engine import edits, numbers
from exam_engine.blueprints.registry import content_dir, get_solver, load_blueprint
from exam_engine.document import verify_snapshot, wording_differences
from exam_engine.errors import EditNotApplicable
from exam_engine.mcq import to_mcq
from exam_engine.pipeline import generate
from hypothesis import given
from hypothesis import strategies as st

OP = numbers.OP
FALLBACK = "These numbers don't make a question the engine can check."


class _Draws:
    """Stands in for Hypothesis' ``data`` so a ``(direction, data)`` invariant test can be
    run on given params."""

    def __init__(self, params: dict):
        self.params = params

    def draw(self, _strategy: object) -> dict:
        return self.params


def _inner(test):
    return test.hypothesis.inner_test


# blueprint -> its invariant, run on an accepted edit's object (the checks re-derive the
# answer from the params or the printed text, independently of solve())
INVARIANTS = {
    "ratio_easy": lambda q: _inner(ratio_inv.test_easy_invariant_second_share_of_two_term_split)(
        params=q["parameters"]
    ),
    "ratio_medium": lambda q: _inner(
        ratio_inv.test_medium_invariant_third_share_of_three_term_split
    )(params=q["parameters"]),
    "percentage_easy": lambda q: _inner(percentage_inv.test_easy_invariant_percent_of_whole)(
        params=q["parameters"]
    ),
    "percentage_medium": lambda q: _inner(percentage_inv.test_medium_invariant_percentage_change)(
        direction=q["parameters"]["direction"], data=_Draws(q["parameters"])
    ),
    "percentage_hard": lambda q: _inner(percentage_inv.test_hard_invariant_reverse_percentage)(
        direction=q["parameters"]["direction"], data=_Draws(q["parameters"])
    ),
    "speed_easy": lambda q: _inner(speed_inv.test_easy_invariant_distance_is_speed_times_time)(
        params=q["parameters"]
    ),
    "speed_medium": lambda q: _inner(
        speed_inv.test_medium_invariant_average_is_total_distance_over_total_time
    )(params=q["parameters"]),
    "speed_hard": lambda q: _inner(speed_inv.test_hard_invariant_combined_speed_closes_the_gap)(
        params=q["parameters"]
    ),
    "fractions_medium": lambda q: _inner(
        fractions_inv.test_medium_invariant_answer_is_fraction_of_the_remainder
    )(params=q["parameters"]),
    "fractions_hard": lambda q: _inner(
        fractions_inv.test_hard_invariant_forward_apply_recovers_the_remainder
    )(params=q["parameters"]),
    "average_easy": average_inv.check_easy,  # reads the numbers back from the printed text
}
ENABLED = sorted(INVARIANTS)


def _free(q: dict) -> dict:
    return {s["key"]: q["parameters"][s["key"]] for s in numbers.number_slots(q["blueprint_code"])}


def test_the_enabled_blueprints_are_exactly_those_marking_free_numbers():
    codes = sorted(p.stem for p in (content_dir() / "blueprints").glob("*.yaml"))
    marked = [c for c in codes if numbers.number_slots(c)]
    assert marked == ENABLED
    assert len(ENABLED) >= 8
    for code in ENABLED:
        assert callable(getattr(get_solver(code), "number_problem", None)), code


def test_free_marks_need_a_number_role_and_a_label():
    from exam_engine.blueprints.base import check_param_roles

    spec = copy.deepcopy(load_blueprint("ratio_easy"))
    spec.param_roles["names"] = {"role": "name", "edit": "free", "label": "Names"}
    spec.param_roles["total"] = {"role": "number", "edit": "free"}
    assert len(check_param_roles("ratio_easy", spec)) == 2


@pytest.mark.parametrize("code", ENABLED)
def test_the_engines_own_numbers_pass_the_gate(code):
    """number_problem never refuses what the sampler makes (it mirrors its construction)."""
    solver = get_solver(code)
    for seed in range(1, 121):
        assert solver.number_problem(generate(code, seed)["parameters"]) is None, (code, seed)


def _check_accepted(source: dict, changes: dict, child: dict) -> None:
    code = source["blueprint_code"]
    assert child["parameters"] == {**source["parameters"], **changes}
    assert child["source_type"] == "generated" and child["seed"] == source["seed"]
    assert child["provenance"]["parent_id"] == source["id"]
    assert child["provenance"]["version"] == source["provenance"]["version"] + 1
    assert verify_snapshot(child) == []
    assert wording_differences(child) == []
    INVARIANTS[code](child)


@st.composite
def _random_edit(draw, code: str):
    """A source question and random free numbers anywhere in each slot's range."""
    source = generate(code, draw(st.integers(1, 400)))
    changes = {}
    for slot in numbers.number_slots(code):
        if not draw(st.booleans()):
            continue
        whole = st.integers(slot["minimum"], slot["maximum"])
        current = source["parameters"][slot["key"]]
        changes[slot["key"]] = (
            draw(st.lists(whole, min_size=len(current), max_size=len(current)))
            if slot["list"]
            else draw(whole)
        )
    return source, changes or _free(source)


@pytest.mark.parametrize("code", ENABLED)
@given(data=st.data())
def test_random_numbers_are_either_proven_or_refused_in_words(code, data):
    source, changes = data.draw(_random_edit(code))
    try:
        child = edits.apply(OP, source, changes=changes)
    except EditNotApplicable as e:
        assert e.reason != FALLBACK, (code, changes)  # number_problem missed a case
        assert e.reason[0].isupper() and e.reason.endswith("."), e.reason
        return
    _check_accepted(source, changes, child)


# the invariant tests' build_object calls `assume`, which always holds here (the edit passed)
@pytest.mark.filterwarnings("ignore:Using `assume` outside")
@pytest.mark.parametrize("code", ENABLED)
def test_another_questions_numbers_are_accepted(code):
    """The numbers of any generated question of the same kind make a valid edit."""
    accepted = 0
    for seed in range(1, 121):
        source, other = generate(code, seed), generate(code, seed + 1000)
        shape = [len(v) if isinstance(v, list) else 0 for v in _free(source).values()]
        if _roles(source, {"choice"}) != _roles(other, {"choice"}) or shape != [
            len(v) if isinstance(v, list) else 0 for v in _free(other).values()
        ]:
            continue  # another choice (direction, template) or count: not the same shape
        child = edits.apply(OP, source, changes=_free(other))
        _check_accepted(source, _free(other), child)
        assert _roles(child, {"name", "item"}) == _roles(source, {"name", "item"})
        accepted += 1
    assert accepted >= 5, code


def _roles(q: dict, roles: set[str]) -> dict:
    spec = load_blueprint(q["blueprint_code"])
    return {k: q["parameters"][k] for k, e in spec.param_roles.items() if e["role"] in roles}


# --- refusals ---------------------------------------------------------------------------


def _ratio() -> dict:
    return generate("ratio_easy", 3)  # Devi and Jia En share $300 in the ratio 9 : 3


@pytest.mark.parametrize(
    ("changes", "says"),
    [
        ({"total": 301}, "The amount must be a multiple of 12"),
        ({"ratio": [4, 4]}, "must not all be the same"),
        ({"total": 5}, "Amount shared ($) must be from 6 to 2000."),
        ({"ratio": [3, 10]}, "Ratio must be from 1 to 9."),
        ({"total": 120.5}, "must be a whole number"),
        ({"total": True}, "must be a whole number"),
        ({"total": "120"}, "must be a whole number"),
        ({"ratio": [3, 4, 5]}, "Ratio needs 2 numbers."),
        ({"ratio": 3}, "Ratio needs 2 numbers."),
        ({"names": ["Ann", "Ben"]}, "is not a number you can change here"),
        ({"bogus": 1}, "is not a number you can change here"),
        ({}, "No numbers were given."),
    ],
)
def test_refusals_say_why(changes, says):
    with pytest.raises(EditNotApplicable) as e:
        edits.apply(OP, _ratio(), changes=changes)
    assert says in e.value.reason


def test_a_choice_parameter_is_not_a_free_number():
    q = generate("percentage_medium", 1)
    with pytest.raises(EditNotApplicable, match="not a number you can change"):
        edits.apply(OP, q, changes={"direction": "increase"})


@pytest.mark.parametrize(
    ("code", "changes", "says"),
    [
        ("percentage_easy", {"percent": 7, "whole": 30}, "but 7% of $30 is not"),
        ("speed_medium", {"t1": 2, "t2": 2}, "The two times must be different."),
        ("speed_medium", {"d1": 60, "t1": 1, "d2": 120, "t2": 2}, "at different speeds"),
        ("speed_hard", {"s1": 30, "s2": 40, "gap": 100}, "combined speed (70 km/h)"),
        ("fractions_medium", {"n1": 3, "d1": 2}, "The fraction 3/2 must be less than 1"),
        ("average_easy", {"values": [1, 1, 1]}, "Each number must be from"),
    ],
)
def test_solver_refusals_are_sentences(code, changes, says):
    q = generate(code, 1)
    if "values" in changes:
        changes = {"values": [1] * len(q["parameters"]["values"])}
    with pytest.raises(EditNotApplicable) as e:
        edits.apply(OP, q, changes=changes)
    assert says in e.value.reason


def test_not_offered_where_it_would_not_be_clean():
    assert edits.applicable(OP, _ratio())
    assert OP not in edits.available_ops(_ratio())  # a form, not a one-click button
    assert not edits.applicable(OP, to_mcq(_ratio(), 1))  # its options would no longer fit
    assert not edits.applicable(OP, edits.apply("change-to-decimals", _ratio()))
    assert not edits.applicable(OP, generate("ratio_structured", 1))  # multi-part
    assert not edits.applicable(OP, generate("ratio_hard", 1))  # no free numbers marked
    sourced = {**_ratio(), "source_type": "sourced"}
    assert not edits.applicable(OP, sourced)
    with pytest.raises(EditNotApplicable):
        edits.apply(OP, to_mcq(_ratio(), 1), changes={"total": 120})


def test_keeps_the_diagram_toggled_off():
    hidden = edits.apply("toggle-diagram", _ratio())
    child = edits.apply(OP, hidden, changes={"total": 120})
    assert child["question"]["parts"][0]["diagram"] is None
    assert verify_snapshot(child) == [] and wording_differences(child) == []


def test_the_bar_model_and_working_follow_the_new_numbers():
    child = edits.apply(OP, _ratio(), changes={"ratio": [3, 4], "total": 140})
    part = child["question"]["parts"][0]
    assert part["answer"]["value"] == 80
    assert "$140" in part["text"] and "3 : 4" in part["text"]
    assert [b["units"] for b in part["diagram"]["bars"]] == [3, 4]
    assert any("20" in s["text"] for s in part["solution_steps"])  # 1 unit = $20
