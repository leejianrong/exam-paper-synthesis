"""Printed maths typography (EXA-142): no raw caret, ``x`` or hyphen reaches a page.

Real keys print ``cm²``, ``speed × time`` and ``30 − 20``; ours printed ``cm^2``, ``speed x time``
and ``30 - 20`` (REAL-PAPER-COMPARISON.md, "Key typography bugs"). A lint over every blueprint:
the rendered student sheet and answer key, as text, must hold none of them. KaTeX math
(``\\(…\\)``) is left out: KaTeX typesets its own ``^``, ``-`` and ``\\times``.
"""

from __future__ import annotations

import html
import re

import pytest
from exam_engine import mcq
from exam_engine.blueprints.registry import content_dir
from exam_engine.pipeline import generate
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.units import printed_unit

CODES = sorted(p.stem for p in (content_dir() / "blueprints").glob("*.yaml"))
SEEDS = range(20)

_NOT_TEXT = re.compile(r"<script.*?</script>|<style.*?</style>", re.S)
_LATEX = re.compile(r"\\\(.*?\\\)", re.S)
BAD = {
    "caret": re.compile(r"\^"),
    # "x" between two operands ("5 x 124", "speed x time")
    "x for ×": re.compile(r"(?<=[\w)%]) x (?=[\w($])"),
    # a hyphen between two amounts: "30 - 20", "$36 - $15", "100% - 35%"
    "hyphen for −": re.compile(r"(?<=[\d%]) ?- ?(?=[\d$])"),
}


def printed_text(page: str) -> str:
    body = _NOT_TEXT.sub("", page.split("<body", 1)[1])
    return _LATEX.sub(" ", html.unescape(re.sub(r"<[^>]+>", " ", body)))


# Algebra's prose may name its letter, "multiplied only x by 8": only a number beside it is ×.
_X_BY_A_NUMBER = re.compile(r"(?<=[\d)%]) x (?=[\w($])|(?<=[\w)%]) x (?=[\d($])")


def typography_errors(text: str, *, letter_x: bool = False) -> list[str]:
    checks = dict(BAD, **({"x for ×": _X_BY_A_NUMBER} if letter_x else {}))
    return [
        f"{name}: …{text[max(0, m.start() - 30) : m.end() + 20]}…"
        for name, pat in checks.items()
        for m in pat.finditer(text)
    ]


def test_the_lint_catches_each_bug() -> None:
    assert typography_errors("Answer: 60 cm^2") and typography_errors("speed x time")
    assert typography_errors("30 - 20 = 10") and typography_errors("$36 - $15")
    assert not typography_errors("Answer: 60 cm² · 3 × 4 − 2 · a 3-digit number · Ah-Huat")
    assert not typography_errors("multiplied only x by 8", letter_x=True)
    assert typography_errors("5 x 124", letter_x=True)


def test_area_and_volume_units_print_with_superscripts() -> None:
    assert [printed_unit(u) for u in ("cm^2", "m^2", "cm^3", "m^3")] == ["cm²", "m²", "cm³", "m³"]
    key = render_answer_key_html("t", [generate("geometry_area_easy", 1)])
    assert re.search(r"Answer: \d+ cm²</p>", key)


def test_an_angle_prints_with_the_degree_sign() -> None:
    key = render_answer_key_html("t", [generate("geometry_angle_easy", 1)])
    assert re.search(r"Answer: \d+°</p>", key) and "degrees</p>" not in key


@pytest.mark.parametrize("code", CODES)
def test_printed_text_has_no_raw_operators(code: str) -> None:
    for seed in SEEDS:
        obj = generate(code, seed)
        objs = [obj]
        if mcq.convertible(obj):
            objs.append(mcq.to_mcq(obj, seed))
        for page in (render_worksheet_html("t", objs), render_answer_key_html("t", objs)):
            errors = typography_errors(printed_text(page), letter_x=code.startswith("algebra"))
            assert not errors, f"{code} seed {seed}: {errors[:3]}"
