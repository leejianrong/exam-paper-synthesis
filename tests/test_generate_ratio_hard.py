"""ratio_hard (V3): before-after with an invariant quantity. Mirrors the
ratio_medium generation suite — schema-valid, tagged hard/non-routine, 4 marks,
a bar_model_before_after aid that passes its consistency check, deterministic,
seeds vary, and hand-verified golden fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exam_engine import generate
from exam_engine.blueprints.registry import get_solver
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden" / "ratio_hard.jsonl"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_is_schema_valid_and_tagged(seed: int):
    obj = generate("ratio_hard", seed)

    assert validate_object(obj) == []
    assert obj["schema_version"] == "1.2.0"
    assert obj["id"] == f"ratio_hard:{seed}"
    assert obj["source_type"] == "generated"
    assert obj["blueprint_code"] == "ratio_hard"
    assert obj["seed"] == seed

    assert obj["cognitive"]["difficulty"] == "hard"
    assert obj["cognitive"]["cognitive_level"] == "non_routine_heuristic"

    parts = obj["question"]["parts"]
    assert len(parts) == 1
    assert obj["question"]["total_marks"] == 4
    assert sum(m["mark"] for m in parts[0]["marking_scheme"]) == 4

    answer = parts[0]["answer"]
    assert answer["type"] == "quantity"
    assert answer["unit"] == "$"
    assert isinstance(answer["value"], int) and answer["value"] > 0

    # The before-after aid rides on the part and is consistent (A5).
    diagram = parts[0]["diagram"]
    assert diagram is not None and diagram["type"] == "bar_model_before_after"
    assert obj["validation"]["checks"]["diagram_consistent"] is True

    assert obj["validation"]["status"] == "pass"
    prov = obj["provenance"]
    assert prov["created_by"] == "engine"
    assert prov["llm_used"] is False
    assert prov["created_at"] is None  # stamped at the API boundary
    assert prov["parent_id"] is None
    assert prov["version"] == 1


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_is_deterministic(seed: int):
    assert generate("ratio_hard", seed) == generate("ratio_hard", seed)


def test_different_seeds_vary():
    ids = {generate("ratio_hard", s)["id"] for s in SEEDS}
    params = [
        (
            tuple(generate("ratio_hard", s)["parameters"]["ratio_before"]),
            tuple(generate("ratio_hard", s)["parameters"]["ratio_after"]),
            generate("ratio_hard", s)["parameters"]["spent"],
        )
        for s in SEEDS
    ]
    assert len(ids) == len(SEEDS)
    assert len(set(params)) > 1


def test_golden_fixtures():
    """Correctness anchor: hand-verified params -> expected answer (ADR-0003)."""
    solver = get_solver("ratio_hard")
    lines = [ln for ln in GOLDEN.read_text().splitlines() if ln.strip()]
    assert lines, "golden fixture file is empty"
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        report = solver.validate(rec["params"], solution)
        assert report["ok"] is True
