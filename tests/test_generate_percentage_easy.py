"""percentage_easy (KAN-149): find X% of a money amount. Mirrors the ratio_easy
generation suite — schema-valid, tagged easy/routine, 2 marks, no diagram,
deterministic, seeds vary, and hand-verified golden fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from exam_engine import generate
from exam_engine.blueprints.registry import get_solver
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden" / "percentage_easy.jsonl"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_is_schema_valid_and_tagged(seed: int):
    obj = generate("percentage_easy", seed)

    assert validate_object(obj) == []
    assert obj["schema_version"] == "1.4.0"
    assert obj["id"] == f"percentage_easy:{seed}"
    assert obj["source_type"] == "generated"
    assert obj["blueprint_code"] == "percentage_easy"
    assert obj["seed"] == seed

    assert obj["cognitive"]["difficulty"] == "easy"
    assert obj["cognitive"]["cognitive_level"] == "routine_procedural"

    parts = obj["question"]["parts"]
    assert len(parts) == 1
    assert obj["question"]["total_marks"] == 2
    assert sum(m["mark"] for m in parts[0]["marking_scheme"]) == 2

    answer = parts[0]["answer"]
    assert answer["type"] == "quantity"
    assert answer["unit"] == "$"
    assert isinstance(answer["value"], int) and answer["value"] > 0

    # This rung has no natural bar-model aid (see KAN-149) — no diagram.
    assert parts[0]["diagram"] is None

    assert obj["validation"]["status"] == "pass"
    prov = obj["provenance"]
    assert prov["created_by"] == "engine"
    assert prov["llm_used"] is False
    assert prov["created_at"] is None  # stamped at the API boundary
    assert prov["parent_id"] is None
    assert prov["version"] == 1


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_is_deterministic(seed: int):
    assert generate("percentage_easy", seed) == generate("percentage_easy", seed)


def test_different_seeds_vary():
    ids = {generate("percentage_easy", s)["id"] for s in SEEDS}
    params = [
        (
            generate("percentage_easy", s)["parameters"]["percent"],
            generate("percentage_easy", s)["parameters"]["whole"],
        )
        for s in SEEDS
    ]
    assert len(ids) == len(SEEDS)
    assert len(set(params)) > 1


def test_golden_fixtures():
    """Correctness anchor: hand-verified params -> expected answer (ADR-0003)."""
    solver = get_solver("percentage_easy")
    lines = [ln for ln in GOLDEN.read_text().splitlines() if ln.strip()]
    assert lines, "golden fixture file is empty"
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        report = solver.validate(rec["params"], solution)
        assert report["ok"] is True
