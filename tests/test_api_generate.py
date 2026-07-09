"""A9 thin API contract (ADR-0006). Logic lives in the engine; this only checks
the wiring returns schema-valid objects and honours count / errors."""

from __future__ import annotations

from app.main import app
from exam_engine.schema import validate_object
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_generate_returns_schema_valid_object():
    resp = client.post("/generate", json={"blueprint_code": "ratio_medium", "seed": 42, "count": 1})
    assert resp.status_code == 200
    questions = resp.json()["questions"]
    assert len(questions) == 1
    obj = questions[0]
    assert validate_object(obj) == []
    # created_at is stamped at the API boundary (ADR-0016).
    assert obj["provenance"]["created_at"] is not None


def test_generate_count_returns_unique_batch():
    resp = client.post("/generate", json={"blueprint_code": "ratio_medium", "seed": 1000, "count": 3})
    assert resp.status_code == 200
    questions = resp.json()["questions"]
    assert len(questions) == 3
    assert len({q["id"] for q in questions}) == 3


def test_unknown_blueprint_is_404():
    resp = client.post("/generate", json={"blueprint_code": "does_not_exist", "count": 1})
    assert resp.status_code == 404


def test_count_bounds_enforced_by_pydantic():
    assert client.post("/generate", json={"count": 0}).status_code == 422
    assert client.post("/generate", json={"count": 999}).status_code == 422
