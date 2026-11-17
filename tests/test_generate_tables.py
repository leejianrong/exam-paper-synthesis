"""Generation suite for the data-table blueprints (EXA-148): the solver's ``table()`` hook
reaches ``question.table``, objects are schema-valid and load-gated, the table prints on the
worksheet and in the key, names are cosmetic, the multiple-choice copy draws on the
distractors hook, and the hand-verified goldens hold. The correctness authority is
``test_invariants_tables.py``; the multi-part ``tariff_gst`` goldens run in
``test_multipart_blueprints.py``."""

from __future__ import annotations

import json
import re
from fractions import Fraction
from pathlib import Path

import pytest
from exam_engine import canonical, edits, generate, mcq
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.document import verify_snapshot
from exam_engine.mcq import _eval
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]
CASES = {
    # code: (level, topic, difficulty, marks per part, answer type)
    "postage_table": ("P5", "Statistics (Tables)", "medium", [2], "decimal"),
    "rental_table": ("P5", "Statistics (Tables)", "hard", [3], "integer"),
    "tariff_gst": ("P6", "Percentage", "hard", [2, 2], "decimal"),
}
SINGLE = ["postage_table", "rental_table"]


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_generate_is_valid_tagged_and_carries_its_table(code, seed):
    level, topic, difficulty, marks, atype = CASES[code]
    obj = generate(code, seed)
    assert validate_object(obj) == []
    canonical.load(obj)
    assert obj["syllabus"]["level"] == level and obj["syllabus"]["topic"] == topic
    assert obj["cognitive"]["difficulty"] == difficulty
    assert [p["marks"] for p in obj["question"]["parts"]] == marks
    assert obj["question"]["total_marks"] == sum(marks)
    assert all(p["answer"]["type"] == atype for p in obj["question"]["parts"])
    table = obj["question"]["table"]
    assert table["caption"] and len(table["headers"]) >= 2 and len(table["rows"]) >= 3
    assert all(isinstance(c, str) and c for row in table["rows"] for c in row)
    assert verify_snapshot(obj) == []


def test_a_blueprint_without_a_table_hook_prints_none():
    assert "table" not in generate("rate_hard", 3)["question"]


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_every_step_carries_an_exact_expr_ending_at_the_answer(code, seed):
    for part in generate(code, seed)["question"]["parts"]:
        values = [_eval(s["expr"] or "") for s in part["solution_steps"]]
        assert all(v is not None for v in values)
        assert values[-1] == Fraction(str(part["answer"]["value"]))


@pytest.mark.parametrize("code", CASES)
def test_deterministic_and_varied(code):
    assert generate(code, 5) == generate(code, 5)
    tables = {json.dumps(generate(code, s)["question"]["table"]) for s in SEEDS}
    assert len(tables) > 1


@pytest.mark.parametrize("code", CASES)
def test_the_table_prints_on_the_worksheet_and_in_the_key(code):
    obj = generate(code, 3)
    sheet = render_worksheet_html("Tables", [obj])
    key = render_answer_key_html("Tables", [obj])
    for html in (sheet, key):
        assert html.count('<table class="content-table">') == 1
        for cell in obj["question"]["table"]["rows"][0]:
            assert f"<td>{cell}</td>" in html
    assert "Answer:" not in sheet and "Answer:" in key


def test_money_prints_at_two_decimal_places():
    obj = generate("tariff_gst", 3)
    key = render_answer_key_html("Tariff", [obj])
    for part in obj["question"]["parts"]:
        assert f"${part['answer']['value']:.2f}" in key
    assert all(re.fullmatch(r"\$\d+\.\d\d", row[-1]) for row in obj["question"]["table"]["rows"])


@pytest.mark.parametrize("code", CASES)
def test_rename_is_cosmetic(code):
    obj = generate(code, 4)
    old = obj["parameters"]["name"]
    child = edits.apply("set-cosmetic", obj, changes={"name": "Nurul Aini"})
    q = child["question"]
    printed = " ".join([q["stem"] or ""] + [p["text"] for p in q["parts"]])
    assert "Nurul Aini" in printed and old not in printed
    assert q["table"] == obj["question"]["table"]
    assert [p["answer"] for p in q["parts"]] == [p["answer"] for p in obj["question"]["parts"]]


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
def test_the_hook_supplies_most_wrong_options(code):
    from_hook = 0
    for seed in range(1, 101):
        obj = generate(code, seed)
        hooked = mcq.common_wrong_answers(obj)
        assert hooked and all(why.strip() for _, why in hooked), seed
        answer = obj["question"]["parts"][0]["answer"]
        hook_texts = {mcq.answer_text(mcq._with_value(answer, v)) for v, _ in hooked}
        m = mcq.to_mcq(obj, seed)
        assert verify_snapshot(m) == [], seed
        assert m["question"]["table"] == obj["question"]["table"]
        choice = m["question"]["parts"][0]["answer"]
        wrong = [o["text"] for o in choice["options"] if o["label"] != choice["correct"]]
        from_hook += sum(t in hook_texts for t in wrong) >= 2
    assert from_hook >= 90


def test_postage_slip_looking_up_the_total_mass_is_offered():
    """Re-derived from the printed table: the postage of the two masses added together."""
    seen = 0
    for seed in range(1, 101):
        obj = generate("postage_table", seed)
        masses = [
            int(m) for m in re.findall(r"mass of (\d+) g", obj["question"]["parts"][0]["text"])
        ]
        combined = sum(masses)
        for label, price in obj["question"]["table"]["rows"]:
            hi = int(re.search(r"up to (\d+) g", label, flags=re.I).group(1))
            lo = int(m.group(1)) if (m := re.search(r"Above (\d+) g", label)) else 0
            if lo < combined <= hi:
                slip = Fraction(price.lstrip("$"))
                assert slip in [v for v, _ in mcq.common_wrong_answers(obj)], seed
                seen += 1
    assert seen >= 30


def test_rental_slip_forgetting_the_first_period_is_offered():
    """Re-derived from the printed question: the extra hours alone, without the first period."""
    for seed in range(1, 101):
        obj = generate("rental_table", seed)
        answer = obj["question"]["parts"][0]["answer"]["value"]
        first = obj["question"]["table"]["headers"][1]
        fh = 1 if first == "First hour" else int(first.split()[1])
        assert answer - fh in [v for v, _ in mcq.common_wrong_answers(obj)], seed
