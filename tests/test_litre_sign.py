"""Litres print as ℓ (and millilitres as mℓ), as on PSLE papers, everywhere the paper, the key
and multiple-choice options print a unit; the stored unit codes stay "l"/"ml"."""

from __future__ import annotations

import copy
import re

from exam_engine import render
from exam_engine.convert import answer_inline
from exam_engine.document import verify_snapshot
from exam_engine.mcq import answer_text, to_mcq
from exam_engine.pipeline import generate
from exam_engine.units import printed_unit


def test_unit_codes_print_as_the_litre_sign():
    assert printed_unit("l") == "ℓ" and printed_unit("ml") == "mℓ"
    assert printed_unit("cm") == "cm" and printed_unit("") == ""
    litres = {"type": "integer", "value": 18, "unit": "l"}
    assert render._fmt_answer(litres) == "18 ℓ"
    assert render.unit_parts("l") == ("", "ℓ") and render.unit_parts("ml") == ("", "mℓ")
    assert answer_inline(litres) == [{"type": "text", "text": "18 ℓ"}]
    assert answer_text(litres) == "18 ℓ"


def test_volume_questions_print_the_litre_sign_and_keep_the_unit_code():
    for code in ("volume_medium", "volume_structured"):
        obj = generate(code, 4)
        html = render.render_answer_key_html("Key", [obj]).split("<body>")[1].split("<script>")[0]
        assert "1 ℓ = 1000 cm³" in html and " ℓ" in html
        assert not re.search(r"\d l\b", html)  # no number followed by a bare l
        units = [p["answer"].get("unit") for p in obj["question"]["parts"]]
        assert "l" in units  # the canonical code is unchanged (schema, goldens, saved papers)


def test_the_font_carries_the_litre_sign_in_inter():
    css = render.font_css()
    assert css.count("unicode-range:U+2113;") == 4  # one per weight/style, family Inter
    assert css.count('font-family:"Inter"') == 16  # 4 weights/styles x latin, ℓ, π, ∠


def test_a_paper_saved_with_the_old_litre_option_still_verifies():
    """A Booklet A question saved before this change has '18 l' as its correct option."""
    m = to_mcq(generate("volume_medium", 2), 5)
    assert verify_snapshot(m) == []
    legacy = copy.deepcopy(m)
    for o in legacy["question"]["parts"][0]["answer"]["options"]:
        o["text"] = o["text"].replace("ℓ", "l")
    assert verify_snapshot(legacy) == []
    wrong = copy.deepcopy(m)
    a = wrong["question"]["parts"][0]["answer"]
    next(o for o in a["options"] if o["label"] == a["correct"])["text"] = "1 l"
    assert verify_snapshot(wrong)
    twice = copy.deepcopy(legacy)
    a = twice["question"]["parts"][0]["answer"]
    right = next(o["text"] for o in a["options"] if o["label"] == a["correct"])
    next(o for o in a["options"] if o["label"] != a["correct"])["text"] = right.replace("l", "ℓ")
    assert verify_snapshot(twice) == ["multiple-choice options must all differ"]
