"""A1 validator seam: a real generated object passes; negative controls fail
with path-pointed errors (R6.2)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from exam_engine import generate
from exam_engine.schema import validate_object

FIXTURES_DIR = Path(__file__).parent / "fixtures"
GOLDEN_DIR = Path(__file__).parent / "golden"


def _valid_obj() -> dict:
    return generate("ratio_medium", 42)


def _valid_choice_answer() -> dict:
    return {
        "type": "choice",
        "options": [
            {"label": "1", "text": "A rectangle"},
            {"label": "2", "text": "A rhombus"},
        ],
        "correct": "2",
    }


def _mcq_part(obj: dict) -> dict:
    """A copy of ``obj`` with its sole part's answer swapped for a valid MCQ."""
    obj = copy.deepcopy(obj)
    obj["question"]["parts"][0]["answer"] = _valid_choice_answer()
    return obj


def test_generated_object_passes():
    assert validate_object(_valid_obj()) == []


def test_stray_field_rejected():
    obj = _valid_obj()
    obj["surprise"] = "nope"  # additionalProperties: false at root
    errors = validate_object(obj)
    assert errors
    assert any("surprise" in e for e in errors)


def test_bad_answer_union_tag_rejected():
    obj = _valid_obj()
    obj["question"]["parts"][0]["answer"]["type"] = "bogus"
    errors = validate_object(obj)
    assert errors
    assert any("answer" in e for e in errors)


def test_out_of_vocab_unit_rejected():
    obj = _valid_obj()
    obj["question"]["parts"][0]["answer"]["unit"] = "bananas"
    errors = validate_object(obj)
    assert errors


def test_generated_missing_blueprint_code_rejected():
    obj = _valid_obj()
    obj["blueprint_code"] = None  # generated => must be a string (allOf if/then)
    errors = validate_object(obj)
    assert errors


def test_errors_are_path_pointed():
    obj = _valid_obj()
    obj["question"]["parts"][0]["marks"] = -1  # minimum: 0
    errors = validate_object(obj)
    assert errors
    assert any(e.startswith("question/parts/0/marks") for e in errors)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda o: o.pop("provenance"),
        lambda o: o["question"].pop("total_marks"),
        lambda o: o["question"].__setitem__("parts", []),  # minItems: 1
    ],
)
def test_structural_controls(mutate):
    obj = _valid_obj()
    mutate(obj)
    assert validate_object(obj)


# --- E2 (KAN-663): schema v2 additions ---------------------------------------
# A3 answer.type:"choice" (MCQ), A4 stem-level question.diagram + angles[].
# part_label, A5 optional part.marks/marking_scheme. All additive on top of
# v1.4.0 — see docs/planning/editor/E2-plan.md.


def test_choice_answer_valid():
    obj = _mcq_part(_valid_obj())
    assert validate_object(obj) == []


@pytest.mark.parametrize("drop", ["options", "correct"])
def test_choice_missing_options_or_correct_rejected(drop):
    obj = _mcq_part(_valid_obj())
    del obj["question"]["parts"][0]["answer"][drop]
    errors = validate_object(obj)
    assert errors


def test_choice_too_few_options_rejected():
    obj = _mcq_part(_valid_obj())
    obj["question"]["parts"][0]["answer"]["options"] = [{"label": "1", "text": "Only one"}]
    assert validate_object(obj)


def test_question_diagram_valid():
    obj = _valid_obj()
    obj["question"]["diagram"] = {
        "type": "shaded_fraction",
        "shape": "rectangle",
        "total_parts": 4,
        "shaded_parts": 1,
    }
    assert validate_object(obj) == []


def test_question_diagram_null_valid():
    obj = _valid_obj()
    obj["question"]["diagram"] = None
    assert validate_object(obj) == []


@pytest.mark.parametrize("part_label", ["a", None])
def test_angle_part_label_valid(part_label):
    obj = _valid_obj()
    obj["question"]["diagram"] = {
        "type": "geometry_figure",
        "unit": "degrees",
        "points": [
            {"id": "A", "x": 0, "y": 0},
            {"id": "B", "x": 4, "y": 0},
            {"id": "C", "x": 2, "y": 3},
        ],
        "angles": [
            {"at": "A", "from": "B", "to": "C", "value_deg": 50, "part_label": part_label},
        ],
    }
    assert validate_object(obj) == []


def test_part_without_marks_or_marking_scheme_valid():
    obj = _valid_obj()
    part = obj["question"]["parts"][0]
    del part["marks"]
    del part["marking_scheme"]
    assert validate_object(obj) == []


def test_v1_4_0_golden_fixtures_still_validate():
    """Additive-only proof (R7.7): every blueprint that shipped a golden fixture
    file before this slice (each ``tests/golden/*.jsonl`` names one blueprint
    code) still produces schema-valid objects, and the pre-existing sourced
    fixture still loads unmodified — under the grown (v1.5.0) schema.

    (The golden ``*.jsonl`` files themselves hold ``{params, expected}`` seed-sweep
    regression anchors, not full canonical objects — see ``tests/invariants.py`` —
    so the proof here is generating a real object per named blueprint, not
    validating the jsonl rows directly.)
    """
    codes = sorted({path.stem for path in GOLDEN_DIR.glob("*.jsonl")})
    assert codes, "expected at least one golden fixture file"
    checked = 0
    for code in codes:
        for seed in (1, 2, 3):
            obj = generate(code, seed)
            errors = validate_object(obj)
            assert errors == [], f"{code} seed={seed}: {errors}"
            checked += 1

    pre_existing_fixture = FIXTURES_DIR / "sourced" / "psle_2023_ratio.json"
    obj = json.loads(pre_existing_fixture.read_text(encoding="utf-8"))
    assert validate_object(obj) == []
    checked += 1

    assert checked > 0
