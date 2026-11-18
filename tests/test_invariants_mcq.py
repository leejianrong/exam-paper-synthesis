"""P8b — independent invariants for multiple choice made from constructed-response questions.

For every blueprint whose answer can be converted, over many seeds: four options that all read
differently, exactly one of which reads as the original (engine-proven) answer does, and it is
the one marked correct; no distractor is worth the same as the answer; the copy passes the
canonical load gate and the document re-solve check; tampering is caught; and the conversion is
deterministic. Checked from the outside (option texts and values), not via ``to_mcq``'s internals.
"""

from __future__ import annotations

import copy
import json
import re
from fractions import Fraction
from pathlib import Path

import pytest
from exam_engine import mcq
from exam_engine.canonical import load
from exam_engine.document import verify_snapshot
from exam_engine.edits import applicable, available_ops
from exam_engine.errors import EditNotApplicable
from exam_engine.mcq import answer_text, convertible, to_mcq
from exam_engine.pipeline import generate

BLUEPRINTS = sorted(
    p.stem
    for p in (Path(__file__).resolve().parents[1] / "engine/exam_engine/content/blueprints").glob(
        "*.yaml"
    )
)
SEEDS = range(1, 31)


def _value(text: str) -> Fraction | None:
    """The number an option shows ("$344", "53 kg", "\\(\\frac{2}{11}\\)", "12.50")."""
    if "frac" in text:
        num, den = text.split("{")[1].split("}")[0], text.split("{")[2].split("}")[0]
        return Fraction(int(num), int(den))
    digits = "".join(ch for ch in text.split(" ")[0] if ch.isdigit() or ch == ".")
    return Fraction(digits) if digits else None


@pytest.mark.parametrize("code", BLUEPRINTS)
def test_every_convertible_blueprint_makes_sound_multiple_choice(code):
    converted = 0
    for seed in SEEDS:
        obj = generate(code, seed)
        if not convertible(obj):
            with pytest.raises(EditNotApplicable):
                to_mcq(obj, seed)
            continue
        converted += 1
        m = to_mcq(obj, seed)
        where = f"{code} seed={seed}"
        answer = m["question"]["parts"][0]["answer"]
        texts = [o["text"] for o in answer["options"]]
        labels = [o["label"] for o in answer["options"]]

        assert labels == ["1", "2", "3", "4"], where
        assert len(set(texts)) == 4, (where, texts)
        right = answer_text(obj["question"]["parts"][0]["answer"])
        assert texts.count(right) == 1, (where, texts, right)
        assert labels[texts.index(right)] == answer["correct"], where

        # no distractor is worth what the answer is worth (no equivalent forms), all positive
        values = [_value(t) for t in texts]
        assert all(v is not None and v > 0 for v in values), (where, texts)
        assert values.count(values[texts.index(right)]) == 1, (where, texts)

        # still a valid, engine-proven canonical object; marks unchanged
        load(copy.deepcopy(m))
        assert verify_snapshot(m) == [], where
        assert m["question"]["total_marks"] == obj["question"]["total_marks"]
        assert (
            sum(x["mark"] for x in m["question"]["parts"][0]["marking_scheme"])
            == (obj["question"]["parts"][0]["marks"])
        )
        # deterministic, and the source object is untouched
        assert json.dumps(to_mcq(obj, seed), sort_keys=True) == json.dumps(m, sort_keys=True)
        assert obj["question"]["parts"][0]["answer"]["type"] != "choice"
    assert converted or code not in ("ratio_easy", "fractions_easy")


def test_tampering_with_the_correct_option_or_its_text_is_caught():
    m = to_mcq(generate("ratio_medium", 3), 7)
    ans = m["question"]["parts"][0]["answer"]

    moved = copy.deepcopy(m)
    a = moved["question"]["parts"][0]["answer"]
    a["correct"] = next(o["label"] for o in a["options"] if o["label"] != ans["correct"])
    assert verify_snapshot(moved)

    retext = copy.deepcopy(m)
    a = retext["question"]["parts"][0]["answer"]
    next(o for o in a["options"] if o["label"] == a["correct"])["text"] = "$1"
    assert verify_snapshot(retext)

    dup = copy.deepcopy(m)
    a = dup["question"]["parts"][0]["answer"]
    right = next(o["text"] for o in a["options"] if o["label"] == a["correct"])
    next(o for o in a["options"] if o["label"] != a["correct"])["text"] = right
    assert verify_snapshot(dup)


def test_a_multiple_choice_copy_offers_no_edit_ops():
    m = to_mcq(generate("ratio_medium", 3), 7)
    assert available_ops(m) == set()
    assert not applicable("set-cosmetic", m)
    assert not applicable("regenerate", m)


def test_stopping_early_is_a_distractor():
    # ratio_medium seed 3: $731 shared 3 : 6 : 8, Ismail gets $344; one unit is $43.
    m = to_mcq(generate("ratio_medium", 3), 1)
    texts = [o["text"] for o in m["question"]["parts"][0]["answer"]["options"]]
    assert "$344" in texts and "$43" in texts


def test_forged_option_lists_are_caught():
    m = to_mcq(generate("ratio_medium", 3), 7)
    ans = m["question"]["parts"][0]["answer"]
    right = next(o for o in ans["options"] if o["label"] == ans["correct"])

    def forged(change):
        f = copy.deepcopy(m)
        change(f["question"]["parts"][0]["answer"])
        return verify_snapshot(f)

    # a look-alike of the correct option (trailing space)
    assert forged(
        lambda a: next(o for o in a["options"] if o["label"] != a["correct"]).update(
            text=right["text"] + " "
        )
    )
    # two options sharing the correct label
    assert forged(
        lambda a: next(o for o in a["options"] if o["label"] != a["correct"]).update(
            label=a["correct"]
        )
    )
    # fewer options
    assert forged(
        lambda a: a.update(
            options=[o for o in a["options"] if o["label"] in ("1", "2", a["correct"])]
        )
    )
    # an option figure
    assert forged(lambda a: a["options"][0].update(diagram={"type": "bar_model"}))


def test_a_question_shown_in_decimals_is_not_converted():
    from exam_engine.edits import apply

    obj = apply("change-to-decimals", generate("ratio_medium", 3), seed=1)
    with pytest.raises(EditNotApplicable):
        to_mcq(obj, 1)


def test_money_distractors_keep_their_cents():
    """A $42.00 answer (stored 42.0, dp 2) must not round a $5.25 step to "$5.20"."""
    for seed in range(40):
        obj = generate("decimals_medium", seed)
        options = to_mcq(obj, seed)["question"]["parts"][0]["answer"]["options"]
        for o in options:
            assert re.fullmatch(r"\$\d+\.\d\d", o["text"]), o["text"]
        for step in obj["question"]["parts"][0]["solution_steps"]:
            v = mcq._eval(step.get("expr") or "")
            shown = f"${v:.2f}" if v is not None and v * 100 == int(v * 100) else None
            if shown and v != Fraction(str(obj["question"]["parts"][0]["answer"]["value"])):
                texts = [o["text"] for o in options]
                rounded = f"${float(v):.1f}0"
                assert rounded == shown or rounded not in texts, (seed, shown, texts)


# --- EXA-122: per-solver common wrong answers + the give-away guard -----------------------


@pytest.mark.parametrize("code", BLUEPRINTS)
def test_the_answer_is_never_guessable_from_the_options(code):
    """Never exactly between two other options, evenly (7/8/9) or by a factor (14/28/56)."""
    for seed in range(1, 61):
        obj = generate(code, seed)
        if not convertible(obj):
            continue
        texts = [o["text"] for o in to_mcq(obj, seed)["question"]["parts"][0]["answer"]["options"]]
        values = [_value(t) for t in texts]
        a = _value(answer_text(obj["question"]["parts"][0]["answer"]))
        for x in values:
            for y in values:
                if x < a < y:
                    assert a - x != y - a and a / x != y / a, (code, seed, texts)


@pytest.mark.parametrize("code", BLUEPRINTS)
def test_every_wrong_option_says_why_it_is_tempting(code):
    obj = generate(code, 2)
    if not convertible(obj):
        pytest.skip("not convertible")
    m = to_mcq(obj, 2)
    part = m["question"]["parts"][0]
    desc = part["marking_scheme"][0]["description"]
    correct = part["answer"]["correct"]
    assert desc.startswith(f"Correct option ({correct}). Wrong options: ")
    for label in ("1", "2", "3", "4"):
        if label != correct:
            assert re.search(rf"\({label}\) \w", desc), desc


def test_a_solver_hook_comes_first_and_never_offers_the_answer(monkeypatch):
    from exam_engine.blueprints.registry import get_solver

    obj = generate("ratio_medium", 3)  # $731 shared 3 : 6 : 8, Ismail gets $344
    solver = get_solver("ratio_medium")
    monkeypatch.setattr(
        solver,
        "distractors",
        lambda params, solution: [
            (solution["answer"]["value"], "the answer itself: must be filtered out"),
            (387, "the other share"),
            (Fraction(1, 3), "not plausible for a whole-number answer: filtered out"),
        ],
        raising=False,
    )
    assert mcq.common_wrong_answers(obj)[1] == (Fraction(387), "the other share")
    assert mcq.distractor_candidates(obj)[0] == (Fraction(387), "the other share")
    m = to_mcq(obj, 1)
    texts = [o["text"] for o in m["question"]["parts"][0]["answer"]["options"]]
    assert "$387" in texts and texts.count("$344") == 1
    assert "the other share" in m["question"]["parts"][0]["marking_scheme"][0]["description"]
    assert verify_snapshot(m) == []


@pytest.mark.parametrize("code", BLUEPRINTS)
def test_an_option_shows_exactly_the_wrong_answer_its_reason_describes(code):
    """A hook's value is never printed rounded (0.05 shown as "0.1" under a reason that
    describes 0.05): the option a teacher reads is the slip the key names."""
    for seed in range(1, 41):
        obj = generate(code, seed)
        if not convertible(obj):
            continue
        hooked = {why: v for v, why in mcq.common_wrong_answers(obj)}
        part = to_mcq(obj, seed)["question"]["parts"][0]
        reasons = dict(
            re.findall(r"\((\d)\) ([^;]+?)(?:;|\.$)", part["marking_scheme"][0]["description"])
        )
        for o in part["answer"]["options"]:
            why = reasons.get(o["label"])
            if why in hooked:
                shown = _value(o["text"])
                assert shown == hooked[why] or any(
                    shown == v for v, w in mcq.common_wrong_answers(obj) if w == why
                ), (code, seed, o["text"], why)


@pytest.mark.parametrize("code", BLUEPRINTS)
def test_money_options_read_whole_dollars_or_two_places(code):
    """A cent-valued wrong answer to a whole-dollar question prints "$19.80", not "$19.8"."""
    for seed in range(1, 61):
        obj = generate(code, seed)
        if not convertible(obj) or obj["question"]["parts"][0]["answer"].get("unit") != "$":
            continue
        for o in to_mcq(obj, seed)["question"]["parts"][0]["answer"]["options"]:
            if o["text"].startswith("$"):
                assert re.fullmatch(r"\$\d+(\.\d\d)?", o["text"]), (code, seed, o["text"])


@pytest.mark.parametrize("code", BLUEPRINTS)
def test_a_fraction_option_never_has_denominator_one(code):
    """EXA-133: a fraction solver's hook value 4/1 printed as "4/1"."""
    for seed in range(1, 61):
        obj = generate(code, seed)
        if not convertible(obj) or obj["question"]["parts"][0]["answer"]["type"] != "fraction":
            continue
        for o in to_mcq(obj, seed)["question"]["parts"][0]["answer"]["options"]:
            assert not re.search(r"\\frac\{\d+\}\{1\}", o["text"]), (code, seed, o["text"])


# EXA-141: real papers list numeric options in ascending order, except "which is the greatest /
# smallest?", where that order would make the answer always (1) or (4).
EXTREME = ("decimals_compare", "fractions_compare")


def _correct_positions(code: str, seeds: range) -> list[int]:
    out = []
    for seed in seeds:
        obj = generate(code, seed)
        if not convertible(obj):
            continue
        answer = to_mcq(obj, seed)["question"]["parts"][0]["answer"]
        out.append(int(answer["correct"]))
    return out


@pytest.mark.parametrize("code", [c for c in BLUEPRINTS if c not in EXTREME])
def test_numeric_options_are_in_ascending_order(code):
    for seed in range(1, 41):
        obj = generate(code, seed)
        if not convertible(obj):
            continue
        texts = [o["text"] for o in to_mcq(obj, seed)["question"]["parts"][0]["answer"]["options"]]
        values = [_value(t) for t in texts]
        assert values == sorted(values), (code, seed, texts)  # type: ignore[type-var]


@pytest.mark.parametrize("code", EXTREME)
def test_a_greatest_or_smallest_question_keeps_a_mixed_order(code):
    positions = _correct_positions(code, range(1, 61))
    assert {2, 3} & set(positions), positions  # not always first or last


def test_the_correct_option_is_not_predictable_from_its_place():
    """Over every convertible blueprint, the correct option sits in each place often enough,
    and no blueprint puts it in the same place nearly every time (which ascending order
    alone would: a rate's "amount in 1 unit" wrong answers are all smaller than the answer)."""
    total = {p: 0 for p in (1, 2, 3, 4)}
    for code in BLUEPRINTS:
        positions = _correct_positions(code, range(1, 41))
        if not positions:
            continue
        for p in positions:
            total[p] += 1
        top = max(positions.count(p) for p in (1, 2, 3, 4))
        assert top <= 0.8 * len(positions), (code, {p: positions.count(p) for p in total})
        # nor is it the largest (or the smallest) option most of the time (EXA-147)
        ends = max(positions.count(1), positions.count(4))
        assert ends <= 0.65 * len(positions), (code, {p: positions.count(p) for p in total})
    n = sum(total.values())
    assert all(0.12 * n <= total[p] <= 0.4 * n for p in total), total


def _hooked() -> list[str]:
    from exam_engine.blueprints.registry import get_solver
    from exam_engine.errors import UnknownBlueprint

    out = []
    for code in BLUEPRINTS:
        try:
            solver = get_solver(code)
        except UnknownBlueprint:  # a sourced-only or unregistered blueprint
            continue
        if hasattr(solver, "distractors") and code not in EXTREME:
            out.append(code)
    return out


@pytest.mark.parametrize("code", _hooked())
def test_a_hooked_answer_is_not_mostly_the_smallest_or_largest(code):
    """EXA-156: a pupil who always picks the smallest (or the largest) option must not score
    well above chance. Over 400 seeds, every blueprint with a distractors hook puts the answer
    first or last at most 40% of the time each, and in every place at least 5% of the time.

    The thresholds come from the data. A hook that goes through ``blueprints.base.spread``
    leads with two slips below, one each side, or two above, so with two on each side the
    answer is first or last 1/6 of the time each. Over 400 seeds the largest end share is now
    34.5% and the smallest place share 5.5% (a hook with only one sensible slip on a side for
    some question forms): 22 seeds against a floor of 20, a margin of 2 seeds. A hook change
    that trips the floor should add a slip on the scarce side rather than lower it. Before
    EXA-156, 25 of these blueprints failed, e.g. rate_easy put the answer (1) 0%, (4) 50%
    of the time and speed_hard (1) 60%, (3) and (4) never."""
    positions = _correct_positions(code, range(1, 401))
    share = {p: positions.count(p) / len(positions) for p in (1, 2, 3, 4)}
    assert share[1] <= 0.4 and share[4] <= 0.4, share
    assert min(share.values()) >= 0.05, share
