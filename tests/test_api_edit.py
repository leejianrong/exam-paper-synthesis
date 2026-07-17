"""V3 thin API contract for POST /edit/{op} (ADR-0006/0009). Logic lives in the
engine; this checks wiring: lineage, created_at stamping, and error mapping."""

from __future__ import annotations

from app.main import app
from exam_engine.schema import validate_object
from fastapi.testclient import TestClient

client = TestClient(app)


def _generate(blueprint_code: str, seed: int) -> dict:
    resp = client.post(
        "/generate", json={"blueprint_code": blueprint_code, "seed": seed, "count": 1}
    )
    assert resp.status_code == 200
    return resp.json()["questions"][0]


def _canonical(obj: dict) -> dict:
    """Drop the UI-only available_ops hint so the strict schema gate accepts it."""
    return {k: v for k, v in obj.items() if k != "available_ops"}


def test_edit_regenerate_stamps_lineage_and_created_at():
    # source carries the available_ops UI hint; the API strips it on entry so the
    # object still round-trips the strict schema gate (KAN-243).
    source = _generate("ratio_medium", 42)
    assert "available_ops" in source
    resp = client.post("/edit/regenerate", json={"question": source, "seed": 7})
    assert resp.status_code == 200
    child = resp.json()["question"]
    assert validate_object(_canonical(child)) == []
    # The child response also carries the freshly-computed available_ops hint.
    assert isinstance(child["available_ops"], list)
    assert child["provenance"]["parent_id"] == source["id"]
    assert child["provenance"]["version"] == source["provenance"]["version"] + 1
    assert child["provenance"]["created_at"] is not None


def test_edit_make_harder_on_hard_is_422():
    hard = _generate("ratio_hard", 3)
    resp = client.post("/edit/make-harder", json={"question": hard, "seed": 1})
    assert resp.status_code == 422


def test_unknown_op_is_404():
    source = _generate("ratio_medium", 42)
    resp = client.post("/edit/frobnicate", json={"question": source})
    assert resp.status_code == 404


def test_malformed_question_is_422():
    resp = client.post("/edit/regenerate", json={"question": {"not": "a canonical object"}})
    assert resp.status_code == 422
