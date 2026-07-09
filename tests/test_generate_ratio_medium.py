"""Primary seam: generate(blueprint_code, seed) -> canonical object (V1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exam_engine import generate
from exam_engine.blueprints.registry import get_solver
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden" / "ratio_medium.jsonl"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_is_schema_valid_and_tagged(seed: int):
    obj = generate("ratio_medium", seed)

    assert validate_object(obj) == []
    assert obj["id"] == f"ratio_medium:{seed}"
    assert obj["source_type"] == "generated"
    assert obj["blueprint_code"] == "ratio_medium"
    assert obj["seed"] == seed

    assert obj["cognitive"]["difficulty"] == "medium"
    assert obj["cognitive"]["cognitive_level"] == "complex_familiar"

    parts = obj["question"]["parts"]
    assert len(parts) == 1
    assert obj["question"]["total_marks"] == 3
    assert sum(m["mark"] for m in parts[0]["marking_scheme"]) == 3

    answer = parts[0]["answer"]
    assert answer["type"] == "quantity"
    assert answer["unit"] == "$"
    assert isinstance(answer["value"], int) and answer["value"] > 0

    assert obj["validation"]["status"] == "pass"
    prov = obj["provenance"]
    assert prov["created_by"] == "engine"
    assert prov["llm_used"] is False
    assert prov["created_at"] is None  # stamped at the API boundary
    assert prov["parent_id"] is None
    assert prov["version"] == 1


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_is_deterministic(seed: int):
    assert generate("ratio_medium", seed) == generate("ratio_medium", seed)


def test_different_seeds_vary():
    ids = {generate("ratio_medium", s)["id"] for s in SEEDS}
    params = [tuple(generate("ratio_medium", s)["parameters"]["ratio"]) for s in SEEDS]
    assert len(ids) == len(SEEDS)
    # not all identical numbers (fresh instances, R1.4)
    assert len(set(params)) > 1


def test_golden_fixtures():
    """Correctness anchor: hand-verified params -> expected answer/marks (ADR-0003)."""
    solver = get_solver("ratio_medium")
    lines = [ln for ln in GOLDEN.read_text().splitlines() if ln.strip()]
    assert lines, "golden fixture file is empty"
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        report = solver.validate(rec["params"], solution)
        assert report["ok"] is True
