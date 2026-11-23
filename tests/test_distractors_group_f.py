"""EXA-122 / EXA-158 — the "common wrong answers" hooks of the P6 chart blueprints
(``pie_fraction``, ``pie_percent_more``, ``pie_fraction_amount``, ``tank_graph``).

For every blueprint, over many seeds through the real ``generate()``: the hook offers named
mistakes, at least two of the multiple-choice copy's three wrong options come from it in most
seeds, and the copy stays engine-proven. Then one named mistake per blueprint is re-derived
*independently* from the printed question (its text and the printed chart) and must be among
the hook's values with that reason.
"""

from __future__ import annotations

import re
from fractions import Fraction

import pytest
from exam_engine import mcq
from exam_engine.document import verify_snapshot
from exam_engine.pipeline import generate

SEEDS = range(1, 101)


def _text(obj: dict) -> str:
    return obj["question"]["parts"][0]["text"]


def _chart(obj: dict) -> dict:
    return obj["question"]["parts"][0]["diagram"]


# --- independent re-derivations: (the mistake's value, a phrase of its reason) -------------


def _pie_fraction(obj: dict) -> tuple[Fraction, str]:
    """Took every sector of the printed pie to be the same size."""
    return Fraction(1, len(_chart(obj)["sectors"])), "same size"


def _pie_percent_more(obj: dict) -> tuple[Fraction, str]:
    """Worked out the first named sector's amount only (its % of the printed total)."""
    m = re.search(r"spent \$(\d+)\. .* on (\w+) than", _text(obj))
    pct = {s["label"].lower(): s["value"] for s in _chart(obj)["sectors"]}
    return Fraction(pct[m[2]] * int(m[1]), 100), "only"


def _pie_fraction_amount(obj: dict) -> tuple[Fraction, str]:
    """Gave the whole: the given amount ÷ its sector's printed fraction."""
    m = re.search(r"spent \$?(\d+)(?: min)? on (\w+)\.", _text(obj))
    sectors = _chart(obj)["sectors"]
    total = sum(s["value"] for s in sectors)
    (known,) = [s for s in sectors if s["label"].lower() == m[2]]
    return int(m[1]) / Fraction(known["value"], total), "the whole"


def _tank(obj: dict) -> tuple[Fraction, str]:
    """A rate: gave the litres that flowed in. A volume: read the later time only."""
    ta, tb = (int(x) for x in re.search(r"from (\d+) min to (\d+) min", _text(obj)).groups())
    level = dict(_chart(obj)["series"][0]["points"])
    if "At what rate" in _text(obj):
        return Fraction(level[tb] - level[ta]), "not the rate"
    return Fraction(level[tb]), f"at {tb} min only"


DERIVE = {
    "pie_fraction": _pie_fraction,
    "pie_percent_more": _pie_percent_more,
    "pie_fraction_amount": _pie_fraction_amount,
    "tank_graph": _tank,
}


@pytest.mark.parametrize("code", DERIVE)
def test_the_hook_supplies_most_wrong_options(code):
    from_hook = 0
    for seed in SEEDS:
        obj = generate(code, seed)
        hooked = mcq.common_wrong_answers(obj)
        assert hooked and all(why.strip() for _, why in hooked), (code, seed)
        answer = obj["question"]["parts"][0]["answer"]
        hook_texts = {mcq.answer_text(mcq._with_value(answer, v)) for v, _ in hooked}
        m = mcq.to_mcq(obj, seed)
        assert verify_snapshot(m) == [], (code, seed)
        choice = m["question"]["parts"][0]["answer"]
        wrong = [o["text"] for o in choice["options"] if o["label"] != choice["correct"]]
        from_hook += sum(t in hook_texts for t in wrong) >= 2
    assert from_hook >= 0.8 * len(SEEDS), (code, from_hook)


@pytest.mark.parametrize("code", DERIVE)
def test_a_named_mistake_is_rederived_from_the_printed_question(code):
    for seed in SEEDS:
        obj = generate(code, seed)
        value, phrase = DERIVE[code](obj)
        hooked = mcq.common_wrong_answers(obj)
        reasons = [why for v, why in hooked if v == value]
        assert reasons, (code, seed, _text(obj), value, hooked)
        assert any(phrase in why for why in reasons), (code, seed, phrase, reasons)
