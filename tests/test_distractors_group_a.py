"""EXA-122 — common-wrong-answer hooks for the Ratio, Percentage, Fractions and Average ladders.

For each blueprint, over many seeds through the real ``generate()``:

* the solver's hook gives wrong answers, each with a reason;
* at least two of the three wrong options of the multiple-choice copy come from the hook
  (in at least 90% of seeds), and the copy is still engine-proven (``verify_snapshot``);
* one named mistake per blueprint is re-derived *independently* from the printed question
  (numbers parsed out of the stem, or the printed figure) and must be among the hook's values,
  so the hook's wrong answers really are what their reasons say.
"""

from __future__ import annotations

import re
from fractions import Fraction
from math import lcm

import pytest
from exam_engine import mcq
from exam_engine.document import verify_snapshot
from exam_engine.pipeline import generate

SEEDS = range(80)

CODES = [
    f"{topic}_{level}"
    for topic in ("ratio", "percentage", "fractions", "average")
    for level in ("easy", "medium", "hard")
]


def _text(obj: dict) -> str:
    return obj["question"]["parts"][0]["text"]


def _money(text: str) -> list[int]:
    return [int(m) for m in re.findall(r"\$(\d+)", text)]


def _ratios(text: str) -> list[list[int]]:
    return [[int(x) for x in m.split(" : ")] for m in re.findall(r"\d+(?: : \d+)+", text)]


def _percent(text: str) -> int:
    return int(re.search(r"(\d+)%", text).group(1))  # type: ignore[union-attr]


def _fractions(text: str) -> list[Fraction]:
    return [Fraction(int(n), int(d)) for n, d in re.findall(r"(\d+)/(\d+)", text)]


def _ints(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", text)]


# --- independent re-derivations: (blueprint, the reason's mistake computed from the stem) ----


def _ratio_easy(obj: dict) -> tuple[Fraction, str]:
    (a, b), total = _ratios(_text(obj))[0], _money(_text(obj))[0]
    other = _text(obj).split(" and ")[0]  # "Gopal and Lucas share $204 ..."
    return Fraction(total * a, a + b), f"{other}'s share"


def _ratio_medium(obj: dict) -> tuple[Fraction, str]:
    ratio, total = _ratios(_text(obj))[0], _money(_text(obj))[0]
    return Fraction(total, sum(ratio)), "found 1 unit only"


def _ratio_hard(obj: dict) -> tuple[Fraction, str]:
    (a, b), (c, d) = _ratios(_text(obj))
    spent = _money(_text(obj))[0]
    common = lcm(b, d)  # the unchanged person's units made equal
    unit = Fraction(spent, a * common // b - c * common // d)
    spender = _text(obj).split(" and ")[0]
    return a * common // b * unit, f"{spender}'s savings at first"


def _percentage_easy(obj: dict) -> tuple[Fraction, str]:
    whole, p = _money(_text(obj))[0], _percent(_text(obj))
    return whole - Fraction(whole * p, 100), "the amount left"


def _percentage_medium(obj: dict) -> tuple[Fraction, str]:
    original, p = _money(_text(obj))[0], _percent(_text(obj))
    return Fraction(original * p, 100), "only, not the new price"


def _percentage_hard(obj: dict) -> tuple[Fraction, str]:
    text = _text(obj)
    new, p = _money(text)[0], _percent(text)
    sign = 1 if "decrease" in text else -1
    return new + sign * Fraction(new * p, 100), "of the new price"


def _fractions_easy(obj: dict) -> tuple[Fraction, str]:
    figure = obj["question"]["parts"][0]["diagram"]  # the printed figure
    total, shaded = figure["total_parts"], figure["shaded_parts"]
    return Fraction(total - shaded, total), "the unshaded part"


def _fractions_medium(obj: dict) -> tuple[Fraction, str]:
    whole, (_, second) = _money(_text(obj))[0], _fractions(_text(obj))
    return whole * second, "of the whole, not of the remainder"


def _fractions_hard(obj: dict) -> tuple[Fraction, str]:
    left, (_, second) = _money(_text(obj))[0], _fractions(_text(obj))
    return left / (1 - second), "after the first purchase only"


def _average_easy(obj: dict) -> tuple[Fraction, str]:
    numbers = _ints(_text(obj))  # the values, then how many there are
    *values, count = numbers
    assert len(values) == count
    return Fraction(sum(values)), "the total"


def _average_medium(obj: dict) -> tuple[Fraction, str]:
    text = _text(obj)
    if "spelling tests" in text:  # n tests; first n-1 scores; the average
        n, *_, avg = _ints(text)
        return Fraction(avg), "the average, not the missing score"
    avg, weeks, _spent = _ints(text)
    return Fraction(avg * weeks), "without taking away the present"


def _average_hard(obj: dict) -> tuple[Fraction, str]:
    text = _text(obj)
    nums = _ints(text)
    if "joined" in text:  # n, old average, n + 1, new average
        return Fraction(nums[3]), "the new average"
    n, before, height = nums[0], nums[1], nums[2]
    return Fraction(n * before - height, n), f"divided by {n}, not {n - 1}"


DERIVE = {
    "ratio_easy": _ratio_easy,
    "ratio_medium": _ratio_medium,
    "ratio_hard": _ratio_hard,
    "percentage_easy": _percentage_easy,
    "percentage_medium": _percentage_medium,
    "percentage_hard": _percentage_hard,
    "fractions_easy": _fractions_easy,
    "fractions_medium": _fractions_medium,
    "fractions_hard": _fractions_hard,
    "average_easy": _average_easy,
    "average_medium": _average_medium,
    "average_hard": _average_hard,
}


def _from_hook(obj: dict, m: dict) -> int:
    """How many of the copy's wrong options are the hook's values."""
    answer = obj["question"]["parts"][0]["answer"]
    hooked = {mcq.answer_text(mcq._with_value(answer, v)) for v, _ in mcq.common_wrong_answers(obj)}
    right = mcq.answer_text(answer)
    texts = [o["text"] for o in m["question"]["parts"][0]["answer"]["options"]]
    return sum(t in hooked for t in texts if t != right)


@pytest.mark.parametrize("code", CODES)
def test_the_hook_supplies_most_wrong_options(code):
    mostly, counted = 0, 0
    for seed in SEEDS:
        obj = generate(code, seed)
        hooked = mcq.common_wrong_answers(obj)
        assert hooked, (code, seed)
        assert all(isinstance(why, str) and why.strip() for _, why in hooked), (code, seed)
        m = mcq.to_mcq(obj, seed)
        assert verify_snapshot(m) == [], (code, seed)
        answer = obj["question"]["parts"][0]["answer"]
        if code == "fractions_easy" and (answer["numerator"], answer["denominator"]) == (1, 2):
            # a half has no unshaded part, ratio or count other than itself and 1/3: the
            # maths leaves one real mistake, the rest are near misses
            continue
        counted += 1
        mostly += _from_hook(obj, m) >= 2
    assert mostly >= 0.9 * counted, (code, mostly, counted)


@pytest.mark.parametrize("code", CODES)
def test_a_named_mistake_is_rederived_from_the_printed_question(code):
    for seed in SEEDS:
        obj = generate(code, seed)
        value, phrase = DERIVE[code](obj)
        hooked = mcq.common_wrong_answers(obj)
        reasons = [why for v, why in hooked if v == value]
        assert reasons, (code, seed, _text(obj), value, hooked)
        assert any(phrase in why for why in reasons), (code, seed, phrase, reasons)


def test_ratio_medium_offers_one_unit_and_another_share():
    # $731 shared 3 : 6 : 8 by Devi, Jia En and Ismail; Ismail gets $344: one unit is $43
    obj = generate("ratio_medium", 3)
    values = dict(mcq.common_wrong_answers(obj))
    assert values[Fraction(43)] == "found 1 unit only"
    assert values[Fraction(129)] == "Devi's share"
    assert values[Fraction(258)] == "Jia En's share"
    texts = [o["text"] for o in mcq.to_mcq(obj, 3)["question"]["parts"][0]["answer"]["options"]]
    assert sorted(texts) == ["$129", "$258", "$344", "$43"]
