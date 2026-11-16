"""Generation suite for the P8e batch 3 one-mark blueprints (EXA-145): rounding, comparing
decimals and fractions, measurement conversion and time durations.

Schema-valid, load-gated, tagged at P5 with 1 mark, deterministic, on no difficulty ladder,
multiple-choice copies that stay engine-proven and read like a real Booklet A question, and
the golden fixtures (regression anchors; a person checks them, see the PR).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from exam_engine import canonical, edits, generate, mcq
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.document import verify_snapshot
from exam_engine.ladder import ladder_for
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]
CASES = {
    # code: (topic, strand, answer type)
    "whole_numbers_rounding": ("Whole Numbers", "Number and Algebra", "integer"),
    "decimals_compare": ("Decimals", "Number and Algebra", "decimal"),
    "fractions_compare": ("Fractions", "Fractions", "fraction"),
    "measurement_conversion": ("Measurement", "Measurement", "integer"),
    "time_duration": ("Time", "Measurement", "integer"),
}


def _options(obj: dict, seed: int) -> tuple[dict, list[str]]:
    m = mcq.to_mcq(obj, seed)
    return m, [o["text"] for o in m["question"]["parts"][0]["answer"]["options"]]


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_generate_is_valid_tagged_and_load_gated(code, seed):
    topic, strand, atype = CASES[code]
    obj = generate(code, seed)
    assert validate_object(obj) == []
    canonical.load(obj)
    assert obj["id"] == f"{code}:{seed}" and obj["blueprint_code"] == code
    assert obj["syllabus"]["level"] == "P5" and obj["syllabus"]["topic"] == topic
    assert obj["syllabus"]["strand"] == strand
    assert obj["cognitive"]["difficulty"] == "easy"
    parts = obj["question"]["parts"]
    assert len(parts) == 1 and obj["question"]["total_marks"] == 1
    assert parts[0]["answer"]["type"] == atype and parts[0]["diagram"] is None
    assert obj["validation"]["status"] == "pass"
    assert obj["provenance"]["llm_used"] is False


@pytest.mark.parametrize("code", CASES)
def test_deterministic_and_varied(code):
    assert generate(code, 5) == generate(code, 5)
    texts = {generate(code, s)["question"]["parts"][0]["text"] for s in SEEDS}
    assert len(texts) == len(SEEDS)


@pytest.mark.parametrize("code", CASES)
def test_on_no_ladder_so_no_harder_or_easier(code):
    """One 1-mark skill each, with no harder rung of the same skill to step to."""
    assert ladder_for(code) is None
    for seed in SEEDS:
        assert edits.available_ops(generate(code, seed)) == {"regenerate"}


@pytest.mark.parametrize("code", CASES)
def test_worksheet_hides_the_answer_and_the_key_shows_it(code):
    obj = generate(code, 3)
    assert "Answer:" not in render_worksheet_html("P", [obj])
    assert "Answer:" in render_answer_key_html("P", [obj])


@pytest.mark.parametrize("code", ["decimals_compare", "fractions_compare"])
def test_compare_options_are_the_four_printed_numbers(code):
    """As on a real paper, the options of "which is the greatest?" are the listed numbers."""
    for seed in range(1, 61):
        obj = generate(code, seed)
        text = obj["question"]["parts"][0]["text"]
        if code == "decimals_compare":
            listed = re.findall(r"\d+\.\d+", text)
        else:
            listed = [
                rf"\(\frac{{{a}}}{{{b}}}\)" for a, b in re.findall(r"frac\{(\d+)\}\{(\d+)\}", text)
            ]
        m, options = _options(obj, seed)
        assert sorted(options) == sorted(listed), (seed, text, options)
        assert verify_snapshot(m) == []


def test_measurement_options_share_the_answers_unit():
    for seed in range(1, 61):
        obj = generate("measurement_conversion", seed)
        unit = re.search(r" in (m|g|mℓ)\.$", obj["question"]["parts"][0]["text"])[1]
        _, options = _options(obj, seed)
        assert all(re.fullmatch(rf"\d+(\.\d)? {unit}", t) for t in options), options
        if unit == "mℓ":  # PSLE prints litres as ℓ, never "ml"
            assert "ml" not in obj["question"]["parts"][0]["text"]


@pytest.mark.parametrize("code", ["whole_numbers_rounding", "time_duration"])
def test_whole_number_options_stay_whole(code):
    for seed in range(1, 61):
        _, options = _options(generate(code, seed), seed)
        assert all(re.fullmatch(r"\d+( min)?", t) for t in options), options


@pytest.mark.parametrize("code", CASES)
def test_golden_fixtures(code):
    """Seed-picked params -> expected answer, checked by a person (ADR-0003)."""
    solver = get_solver(code)
    lines = [ln for ln in (GOLDEN / f"{code}.jsonl").read_text().splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        assert solver.validate(rec["params"], solution)["ok"] is True
        assert load_blueprint(code).marks == rec["expected"]["total_marks"]
