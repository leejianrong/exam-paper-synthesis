"""Independent correctness authority for ``measurement_conversion`` (P8e batch 3, EXA-145).

The check reads the measurement back out of the *printed question* and converts the
*answer* back the other way: the answer in the smaller unit, split into thousands and the
rest, must print as the question's measurement (``3450 m`` -> ``3.45 km``; ``2075 g`` ->
``2 kg 75 g``). ``solve()`` goes forwards (× 1000, or whole × 1000 + part); this goes
backwards with ``divmod`` and string formatting, so a slip in either shows.

The units are checked as printed: litres as ℓ / mℓ (PSLE style), the answer in the unit the
question asks for.

Two input sources: a Hypothesis property test over the parameter space (via
:func:`strategies.build_object`) and a seed sweep through the real pipeline (``generate``).
"""

from __future__ import annotations

import re

from exam_engine import generate
from exam_engine.units import printed_unit
from hypothesis import given
from hypothesis import strategies as st
from invariants import single_part_answer
from strategies import build_object

SWEEP = range(1, 301)
SMALLER = {"km": "m", "kg": "g", "ℓ": "mℓ"}


def check(obj: dict) -> None:
    text = obj["question"]["parts"][0]["text"]
    m = re.fullmatch(r"Express (.+) (km|kg|ℓ)(?: (\d+) (m|g|mℓ))? in (m|g|mℓ)\.", text)
    assert m, text
    amount, big, part, small_in_stem, small = m[1], m[2], m[3], m[4], m[5]
    assert SMALLER[big] == small  # asks for the matching smaller unit
    answer = single_part_answer(obj)
    assert answer["type"] == "integer" and printed_unit(answer["unit"]) == small
    thousands, rest = divmod(answer["value"], 1000)
    if part is None:  # "3.45 km": the answer / 1000, without trailing zeros
        assert re.fullmatch(r"\d\.\d{1,3}", amount) and not amount.endswith("0"), text
        back = f"{thousands}.{rest:03d}".rstrip("0")
        assert back == amount, (text, answer["value"])
    else:  # "2 kg 75 g"
        assert small_in_stem == small
        assert (thousands, rest) == (int(amount), int(part)), (text, answer["value"])
        assert 0 < rest < 1000


@st.composite
def params(draw) -> dict:
    form = draw(st.sampled_from(["decimal", "mixed"]))
    part = draw(st.integers(1, 999))
    return {
        "pair": draw(st.sampled_from(["km_m", "kg_g", "l_ml"])),
        "form": form,
        "whole": draw(st.integers(1, 9)),
        "part": part,
    }


@given(p=params())
def test_answer_converts_back_to_the_printed_measurement(p):
    check(build_object("measurement_conversion", p))


def test_seed_sweep_through_the_real_sampler():
    seen = set()
    for seed in SWEEP:
        obj = generate("measurement_conversion", seed)
        check(obj)
        p = obj["parameters"]
        seen.add((p["pair"], p["form"]))
    assert len(seen) == 6  # every unit pair in both forms
