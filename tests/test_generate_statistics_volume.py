"""Generation suite for the T7 ladders (Statistics (Charts), Volume): schema-valid,
load-gated, tagged, deterministic, figure present and rendering, hand-verified goldens."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from exam_engine import canonical, generate
from exam_engine.blueprints.registry import get_solver
from exam_engine.ladder import ladder_for, sibling
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]
CASES = {
    # code: (difficulty, cognitive_level, marks, diagram type)
    "statistics_chart_easy": ("easy", "routine_procedural", 1, "chart"),
    "statistics_chart_medium": ("medium", "complex_familiar", 2, "chart"),
    "statistics_chart_hard": ("hard", "non_routine_heuristic", 3, "chart"),
    "volume_easy": ("easy", "routine_procedural", 1, "solid"),
    "volume_medium": ("medium", "complex_familiar", 2, "solid"),
    "volume_hard": ("hard", "non_routine_heuristic", 3, "panels"),
}


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_generate_is_valid_tagged_and_load_gated(code, seed):
    difficulty, level, marks, dtype = CASES[code]
    obj = generate(code, seed)
    assert validate_object(obj) == []
    canonical.load(obj)  # semantic gate: chart/solid/panels consistency
    assert obj["id"] == f"{code}:{seed}" and obj["blueprint_code"] == code
    assert obj["cognitive"]["difficulty"] == difficulty
    assert obj["cognitive"]["cognitive_level"] == level
    parts = obj["question"]["parts"]
    assert len(parts) == 1 and obj["question"]["total_marks"] == marks
    assert sum(m["mark"] for m in parts[0]["marking_scheme"]) == marks
    assert parts[0]["diagram"]["type"] == dtype
    assert parts[0]["answer"]["value"] > 0
    assert obj["validation"]["status"] == "pass"
    assert obj["provenance"]["llm_used"] is False


@pytest.mark.parametrize("code", CASES)
def test_deterministic_and_varied(code):
    assert generate(code, 5) == generate(code, 5)
    texts = {generate(code, s)["question"]["parts"][0]["text"] for s in SEEDS}
    assert len(texts) > 1


@pytest.mark.parametrize("code", CASES)
def test_worksheet_shows_the_figure_but_not_the_answer(code):
    obj = generate(code, 3)
    sheet = render_worksheet_html("T7", [obj])
    key = render_answer_key_html("T7", [obj])
    assert '<figure class="diagram"><svg' in sheet and "Answer:" not in sheet
    assert "Answer:" in key


@pytest.mark.parametrize("code", CASES)
def test_golden_fixtures(code):
    """Hand-verified params -> expected answer (ADR-0003)."""
    solver = get_solver(code)
    lines = [ln for ln in (GOLDEN / f"{code}.jsonl").read_text().splitlines() if ln.strip()]
    assert lines
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        assert solver.validate(rec["params"], solution)["ok"] is True


def test_ladders_are_wired():
    for prefix in ("statistics_chart", "volume"):
        rungs = [f"{prefix}_{d}" for d in ("easy", "medium", "hard")]
        assert ladder_for(rungs[1]) == rungs
        assert sibling(rungs[0], +1) == rungs[1] and sibling(rungs[2], -1) == rungs[1]
        assert sibling(rungs[0], -1) is None and sibling(rungs[2], +1) is None
