"""Generation suite for the pie-chart and tank line-graph blueprints (EXA-158): objects are
schema-valid, load-gated and tagged for the paper generator, the figure is drawn from the
params, names and vessels are cosmetic, the multiple-choice copy draws on the distractors hook,
and the hand-verified goldens hold. The correctness authority is
``test_invariants_pie_chart.py`` and ``test_invariants_tank_graph.py``; the multi-part
``tank_graph_structured`` goldens run in ``test_multipart_blueprints.py``."""

from __future__ import annotations

import json
import re
from fractions import Fraction
from pathlib import Path

import pytest
from exam_engine import canonical, edits, generate, mcq
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.document import verify_snapshot, wording_differences
from exam_engine.mcq import _eval
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]
CASES = {
    # code: (difficulty, marks per part, answer type)
    "pie_fraction": ("easy", [1], "fraction"),
    "pie_percent_more": ("medium", [2], "integer"),
    "pie_fraction_amount": ("hard", [3], "integer"),
    "tank_graph": ("medium", [2], "integer"),
    "tank_graph_structured": ("hard", [2, 2], "integer"),
}
SINGLE = [c for c in CASES if c != "tank_graph_structured"]


def figure(obj: dict) -> dict:
    """The chart: the shared stem's figure on the two-part question, else part (a)'s."""
    q = obj["question"]
    return q.get("diagram") or q["parts"][0]["diagram"]


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_generate_is_valid_tagged_and_draws_its_chart(code, seed):
    difficulty, marks, atype = CASES[code]
    obj = generate(code, seed)
    assert validate_object(obj) == []
    canonical.load(obj)
    assert obj["syllabus"]["level"] == "P6"
    assert obj["syllabus"]["topic"] == "Statistics (Charts)"
    assert obj["cognitive"]["difficulty"] == difficulty
    assert [p["marks"] for p in obj["question"]["parts"]] == marks
    assert all(p["answer"]["type"] == atype for p in obj["question"]["parts"])
    assert figure(obj)["type"] == "chart"
    assert verify_snapshot(obj) == [] and wording_differences(obj) == []


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_every_step_carries_an_exact_expr_ending_at_the_answer(code, seed):
    for part in generate(code, seed)["question"]["parts"]:
        values = [_eval(s["expr"] or "") for s in part["solution_steps"]]
        assert all(v is not None for v in values)
        a = part["answer"]
        want = Fraction(a["numerator"], a["denominator"]) if "numerator" in a else a["value"]
        assert values[-1] == want


@pytest.mark.parametrize("code", CASES)
def test_deterministic_and_varied(code):
    assert generate(code, 5) == generate(code, 5)
    figures = {json.dumps(figure(generate(code, s))) for s in SEEDS}
    assert len(figures) > 1


@pytest.mark.parametrize("code", CASES)
def test_the_chart_prints_on_the_worksheet_and_in_the_key(code):
    obj = generate(code, 3)
    for html in (render_worksheet_html("Charts", [obj]), render_answer_key_html("Charts", [obj])):
        assert html.count("<svg") >= 1


def test_a_rate_prints_in_litres_per_minute():
    obj = next(
        o for s in range(1, 50) if (o := generate("tank_graph", s))["parameters"]["ask"] == "rate"
    )
    assert f"{obj['question']['parts'][0]['answer']['value']} ℓ/min" in render_answer_key_html(
        "Tank", [obj]
    )


@pytest.mark.parametrize(
    ("code", "key", "new"),
    [
        ("pie_fraction", "name", "Nurul Aini"),
        ("pie_percent_more", "name", "Nurul Aini"),
        ("pie_fraction_amount", "name", "Nurul Aini"),
        ("tank_graph", "vessel", "barrel"),
        ("tank_graph_structured", "vessel", "barrel"),
    ],
)
def test_rename_is_cosmetic(code, key, new):
    obj = next(o for s in range(1, 50) if (o := generate(code, s))["parameters"][key] != new)
    child = edits.apply("set-cosmetic", obj, changes={key: new})
    q = child["question"]
    printed = " ".join([q["stem"] or ""] + [p["text"] for p in q["parts"]])
    assert new in printed
    assert [p["answer"] for p in q["parts"]] == [p["answer"] for p in obj["question"]["parts"]]
    assert figure(child) == figure(obj)


@pytest.mark.parametrize("code", SINGLE)
def test_golden_fixtures(code):
    """Hand-verified params -> expected answer (ADR-0003)."""
    solver = get_solver(code)
    lines = [ln for ln in (GOLDEN / f"{code}.jsonl").read_text().splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        assert solver.validate(rec["params"], solution)["ok"] is True
        assert load_blueprint(code).marks == rec["expected"]["total_marks"]


# ------------------------------------------------------------------ multiple choice


@pytest.mark.parametrize("code", SINGLE)
def test_the_multiple_choice_copy_is_proven_and_uses_the_hook(code):
    from_hook = 0
    for seed in range(1, 101):
        obj = generate(code, seed)
        hooked = mcq.common_wrong_answers(obj)
        assert hooked and all(why.strip() for _, why in hooked), seed
        answer = obj["question"]["parts"][0]["answer"]
        hook_texts = {mcq.answer_text(mcq._with_value(answer, v)) for v, _ in hooked}
        m = mcq.to_mcq(obj, seed)
        assert verify_snapshot(m) == [] and wording_differences(m) == [], seed
        assert m["question"]["parts"][0]["diagram"] == obj["question"]["parts"][0]["diagram"]
        choice = m["question"]["parts"][0]["answer"]
        wrong = [o["text"] for o in choice["options"] if o["label"] != choice["correct"]]
        from_hook += sum(t in hook_texts for t in wrong) >= 2
    assert from_hook >= 80


@pytest.mark.parametrize("code", SINGLE)
def test_the_answer_moves_over_all_four_options(code):
    places: dict[str, int] = {}
    for seed in range(1, 201):
        choice = mcq.to_mcq(generate(code, seed), seed)["question"]["parts"][0]["answer"]
        places[choice["correct"]] = places.get(choice["correct"], 0) + 1
    assert set(places) == {"1", "2", "3", "4"}, places


def test_the_structured_question_is_not_turned_into_multiple_choice():
    with pytest.raises(Exception, match="not applicable"):
        mcq.to_mcq(generate("tank_graph_structured", 1), 1)


def test_a_fraction_pie_answer_is_not_the_smaller_of_a_pair_summing_to_1():
    """Review of #258: with "the labelled sectors added up" (1 − answer) as an option, the only
    pair of options summing to 1 held the answer, and its smaller member won 82% of the time.
    A pupil playing that trick must do no better than a blind guess (25%)."""
    wins = 0
    for seed in range(1, 401):
        choice = mcq.to_mcq(generate("pie_fraction", seed), seed)["question"]["parts"][0]["answer"]
        vals = {
            o["label"]: Fraction(
                *map(int, re.search(r"frac\{(\d+)\}\{(\d+)\}", o["text"]).groups())
            )
            for o in choice["options"]
        }
        pairs = [(x, y) for x in vals for y in vals if x < y and vals[x] + vals[y] == 1]
        if len(pairs) == 1:
            wins += min(pairs[0], key=vals.__getitem__) == choice["correct"]
    assert wins / 400 <= 0.25, wins


@pytest.mark.parametrize("code", ["tank_graph", "tank_graph_structured"])
def test_the_tap_is_turned_off_in_about_a_third_of_the_graphs(code):
    """Review of #258: the flat stretch was chosen inside the rejection loop and came out in ~70%
    of graphs; it is meant to be about 30%."""
    flat = 0
    for seed in range(1, 401):
        q = generate(code, seed)["question"]
        flat += "turned off" in " ".join([q["stem"] or ""] + [p["text"] for p in q["parts"]])
    assert 0.2 <= flat / 400 <= 0.4, flat


def test_an_empty_tank_is_said_to_be_empty():
    for seed in range(1, 200):
        obj = generate("tank_graph", seed)
        part = obj["question"]["parts"][0]
        empty = obj["parameters"]["volumes"][0] == 0
        assert ("into an empty" in part["text"]) == empty
        assert "there were 0 ℓ" not in part["solution_steps"][0]["text"]


def test_the_tank_graph_belongs_to_the_shared_stem():
    """Real papers print the graph after the shared stem, before (a), not under (a)'s text."""
    obj = generate("tank_graph_structured", 1)
    q = obj["question"]
    assert q["diagram"]["type"] == "chart" and all(p["diagram"] is None for p in q["parts"])
    html = render_worksheet_html("Tank", [obj])
    assert html.index(q["stem"][:30]) < html.index("<svg") < html.index("At what rate")
