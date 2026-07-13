"""A1 validator seam: a real generated object passes; negative controls fail
with path-pointed errors (R6.2)."""

from __future__ import annotations

import pytest
from exam_engine import generate
from exam_engine.schema import validate_object


def _valid_obj() -> dict:
    return generate("ratio_medium", 42)


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
