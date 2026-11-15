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
from fractions import Fraction
from pathlib import Path

import pytest
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
