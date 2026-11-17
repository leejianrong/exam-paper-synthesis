"""P8c — multi-part blueprints: generation, the framework seam, verify_snapshot, edits,
printing, and the hand-verified goldens.

The independent correctness authority is ``test_invariants_structured.py``; this suite
covers everything around it.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from documents import make_doc, question_block
from exam_engine import canonical, edits, generate
from exam_engine.blueprints.base import BlueprintSpec, check_parts
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.document import validate_document, verify_snapshot
from exam_engine.errors import EditNotApplicable
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden"
CODES = {
    # code: (topic, marks per part)
    "ratio_structured": ("Ratio", [2, 3]),
    "speed_structured": ("Speed", [1, 3]),
    "volume_structured": ("Volume", [2, 3]),
    "geometry_angle_structured": ("Geometry (Angles)", [2, 2]),  # EXA-150
}
SEEDS = range(1, 151)


# --- the blueprint marker the paper generator reads ----------------------------------


@pytest.mark.parametrize("code", CODES)
def test_spec_says_it_is_multipart(code):
    spec = load_blueprint(code)
    topic, marks = CODES[code]
    assert spec.is_multipart and spec.part_count == len(marks)
    assert [p["marks"] for p in spec.parts] == marks and spec.marks == sum(marks)
    assert spec.syllabus["topic"] == topic and spec.syllabus["level"] == "P6"


def test_single_part_blueprints_are_unchanged():
    spec = load_blueprint("ratio_hard")
    assert not spec.is_multipart and spec.part_count == 1 and spec.parts == []
    assert generate("ratio_hard", 3)["question"]["parts"][0]["label"] == ""


def test_check_parts_reports_inconsistent_parts():
    spec = copy.deepcopy(load_blueprint("volume_structured"))
    assert check_parts("v", spec) == []
    spec.parts[1]["label"] = "c"
    spec.parts[0]["marks"] = 3
    errors = " ".join(check_parts("v", spec))
    assert "labelled 'c', not 'b'" in errors
    assert "part (a) marking_scheme sums to 2, marks=3" in errors
    assert "parts' marks sum to 6 but blueprint marks=5" in errors
    spec.parts = spec.parts[:1]
    assert "at least two parts" in " ".join(check_parts("v", spec))


def test_assemble_refuses_a_wrong_number_of_answers():
    spec: BlueprintSpec = load_blueprint("speed_structured")
    params = {"name": "Ben", "speed_out": 60, "time_out": 2, "speed_back": 40}
    solution = get_solver("speed_structured").solve(params)
    solution["answers"] = solution["answers"][:1]
    with pytest.raises(canonical.CanonicalValidationError, match="1 answers for 2 parts"):
        canonical.assemble(spec, seed=1, params=params, solution=solution, report={"ok": True})


# --- generation ----------------------------------------------------------------------


@pytest.mark.parametrize("code", CODES)
def test_generated_objects_are_valid_lettered_and_engine_proven(code):
    _, marks = CODES[code]
    for seed in SEEDS:
        obj = generate(code, seed)
        assert validate_object(obj) == []
        q = obj["question"]
        assert q["stem"] and q["total_marks"] == sum(marks)
        assert [p["label"] for p in q["parts"]] == ["a", "b"][: len(marks)]
        assert [p["marks"] for p in q["parts"]] == marks
        for p in q["parts"]:
            assert sum(m["mark"] for m in p["marking_scheme"]) == p["marks"]
            assert p["answer"]["value"] > 0 and p["solution_steps"]
        assert obj["validation"]["status"] == "pass"
        assert obj["provenance"]["llm_used"] is False
        assert verify_snapshot(obj) == [], (code, seed)


@pytest.mark.parametrize("code", CODES)
def test_deterministic_and_varied(code):
    assert generate(code, 5) == generate(code, 5)
    stems = {generate(code, s)["question"]["stem"] for s in range(1, 9)}
    assert len(stems) > 1


@pytest.mark.parametrize("code", CODES)
def test_golden_fixtures(code):
    """Hand-verified params -> every part's expected answer (ADR-0003)."""
    spec = load_blueprint(code)
    solver = get_solver(code)
    lines = [ln for ln in (GOLDEN / f"{code}.jsonl").read_text().splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answers"] == rec["expected"]["answers"]
        assert solver.validate(rec["params"], solution)["ok"] is True
        assert [p["marks"] for p in spec.parts] == rec["expected"]["marks"]
        assert spec.marks == rec["expected"]["total_marks"]


# --- verify_snapshot: every part is checked ------------------------------------------


@pytest.mark.parametrize("code", CODES)
@pytest.mark.parametrize("part", [0, 1])
def test_tampering_with_any_part_answer_is_caught(code, part):
    obj = generate(code, 11)
    obj["question"]["parts"][part]["answer"]["value"] += 1
    label = "ab"[part]
    assert verify_snapshot(obj) == [f"part ({label}) answer does not match the engine's solution"]


@pytest.mark.parametrize("code", CODES)
@pytest.mark.parametrize("part", [0, 1])
def test_tampering_with_any_part_marks_is_caught(code, part):
    obj = generate(code, 12)
    obj["question"]["parts"][part]["marks"] += 1
    obj["question"]["total_marks"] += 1  # even with the total kept consistent
    errors = verify_snapshot(obj)
    assert any(f"part ({'ab'[part]}) marks do not match" in e for e in errors), errors
    assert any(e.startswith("marks do not match blueprint") for e in errors), errors


def test_dropping_reordering_or_relabelling_parts_is_caught():
    obj = generate("ratio_structured", 4)
    dropped = copy.deepcopy(obj)
    dropped["question"]["parts"].pop()
    assert verify_snapshot(dropped) == ["a generated ratio_structured question has exactly 2 parts"]
    swapped = copy.deepcopy(obj)
    swapped["question"]["parts"].reverse()
    assert verify_snapshot(swapped)
    relabelled = copy.deepcopy(obj)
    relabelled["question"]["parts"][1]["label"] = "c"
    assert verify_snapshot(relabelled) == ["part 1 must be labelled (b)"]


def test_a_document_carrying_a_multipart_question_validates_and_catches_tampering():
    obj = generate("volume_structured", 2)
    assert validate_document(make_doc(question_block(obj))) == []
    obj["question"]["parts"][1]["answer"]["value"] = 999
    errors = validate_document(make_doc(question_block(obj)))
    assert errors and "part (b) answer does not match" in errors[0]


# --- edits ---------------------------------------------------------------------------


@pytest.mark.parametrize("code", CODES)
def test_only_whole_question_edits_are_offered(code):
    obj = generate(code, 6)
    assert edits.available_ops(obj) == {"regenerate"}
    for op in ("change-to-decimals", "toggle-diagram", "toggle-bar-view", "make-harder"):
        with pytest.raises(EditNotApplicable):
            edits.apply(op, obj)


@pytest.mark.parametrize("code", CODES)
def test_regenerate_gives_a_proven_multipart_child(code):
    obj = generate(code, 6)
    child = edits.apply("regenerate", obj)
    assert len(child["question"]["parts"]) == 2
    assert child["provenance"]["parent_id"] == obj["id"]
    assert verify_snapshot(child) == []


def test_set_cosmetic_renames_through_every_part_and_keeps_the_answers():
    obj = generate("ratio_structured", 9)
    old = obj["parameters"]["names"]
    child = edits.apply("set-cosmetic", obj, changes={"names": ["Zara", "Yusof"], "item": "beads"})
    q = child["question"]
    text = q["stem"] + " ".join(p["text"] for p in q["parts"])
    assert "Zara" in text and "Yusof" in text and "beads" in text
    assert not any(n in text for n in old)
    assert [p["answer"] for p in q["parts"]] == [p["answer"] for p in obj["question"]["parts"]]
    assert verify_snapshot(child) == []


# --- printing ------------------------------------------------------------------------


@pytest.mark.parametrize("code", CODES)
def test_worksheet_prints_stem_and_lettered_parts_and_key_prints_every_answer(code):
    obj = generate(code, 3)
    sheet = render_worksheet_html("P8c", [obj])
    key = render_answer_key_html("P8c", [obj])
    assert '<span class="part-label">(a)</span>' in sheet
    assert '<span class="part-label">(b)</span>' in sheet
    assert "Answer:" not in sheet
    for part in obj["question"]["parts"]:
        assert str(part["answer"]["value"]) in key
