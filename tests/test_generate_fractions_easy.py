"""fractions_easy (KAN-232): read the fraction of a figure that is shaded.
Mirrors the ratio/percentage easy suites — schema-valid, tagged easy/routine,
1 mark, carries the MANDATORY shaded_fraction figure (plan D1), deterministic,
seeds vary, and hand-verified golden fixtures."""

from __future__ import annotations

import json
from math import gcd
from pathlib import Path

import pytest
from exam_engine import generate
from exam_engine.blueprints.registry import get_solver
from exam_engine.edits import available_ops
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden" / "fractions_easy.jsonl"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_is_schema_valid_and_tagged(seed: int):
    obj = generate("fractions_easy", seed)

    assert validate_object(obj) == []
    assert obj["schema_version"] == "1.4.0"
    assert obj["id"] == f"fractions_easy:{seed}"
    assert obj["source_type"] == "generated"
    assert obj["blueprint_code"] == "fractions_easy"
    assert obj["seed"] == seed

    assert obj["cognitive"]["difficulty"] == "easy"
    assert obj["cognitive"]["cognitive_level"] == "routine_procedural"

    parts = obj["question"]["parts"]
    assert len(parts) == 1
    assert obj["question"]["total_marks"] == 1
    assert sum(m["mark"] for m in parts[0]["marking_scheme"]) == 1

    answer = parts[0]["answer"]
    assert answer["type"] == "fraction"
    assert 0 < answer["numerator"] < answer["denominator"]
    assert gcd(answer["numerator"], answer["denominator"]) == 1  # simplest form

    # Plan D1: the MANDATORY shaded_fraction figure equals the answer fraction.
    diagram = parts[0]["diagram"]
    assert diagram is not None and diagram["type"] == "shaded_fraction"
    assert diagram["total_parts"] == answer["denominator"]
    assert diagram["shaded_parts"] == answer["numerator"]
    assert diagram["shape"] in {"rectangle", "circle", "bar"}
    assert obj["validation"]["checks"]["diagram_consistent"] is True

    assert obj["validation"]["status"] == "pass"
    prov = obj["provenance"]
    assert prov["created_by"] == "engine"
    assert prov["llm_used"] is False
    assert prov["created_at"] is None
    assert prov["parent_id"] is None
    assert prov["version"] == 1


@pytest.mark.parametrize("seed", SEEDS)
def test_mandatory_figure_offers_no_toggle_diagram(seed: int):
    """The shaded_fraction figure is mandatory, so toggle-diagram must NOT be
    offered (the merged available_ops fix keys on aid types only)."""
    obj = generate("fractions_easy", seed)
    ops = available_ops(obj)
    assert "toggle-diagram" not in ops
    assert "change-to-decimals" not in ops  # no money keys on this rung
    assert "regenerate" in ops


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_is_deterministic(seed: int):
    assert generate("fractions_easy", seed) == generate("fractions_easy", seed)


def test_different_seeds_vary():
    ids = {generate("fractions_easy", s)["id"] for s in SEEDS}
    fractions = {
        (
            generate("fractions_easy", s)["parameters"]["numerator"],
            generate("fractions_easy", s)["parameters"]["denominator"],
        )
        for s in SEEDS
    }
    assert len(ids) == len(SEEDS)
    assert len(fractions) > 1


def test_golden_fixtures():
    """Correctness anchor: hand-verified params -> expected answer (ADR-0003)."""
    solver = get_solver("fractions_easy")
    lines = [ln for ln in GOLDEN.read_text().splitlines() if ln.strip()]
    assert lines, "golden fixture file is empty"
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        report = solver.validate(rec["params"], solution)
        assert report["ok"] is True
