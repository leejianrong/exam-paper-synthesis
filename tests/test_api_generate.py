"""A9 thin API contract (ADR-0006). Logic lives in the engine; this only checks
the wiring returns schema-valid objects and honours count / errors."""

from __future__ import annotations

from app.main import app
from exam_engine.schema import validate_object
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def _canonical(obj: dict) -> dict:
    """Drop the UI-only available_ops hint so the strict schema gate accepts it."""
    return {k: v for k, v in obj.items() if k != "available_ops"}


def test_generate_returns_schema_valid_object():
    resp = client.post("/generate", json={"blueprint_code": "ratio_medium", "seed": 42, "count": 1})
    assert resp.status_code == 200
    questions = resp.json()["questions"]
    assert len(questions) == 1
    obj = questions[0]
    # available_ops is a UI-only envelope hint (KAN-243), not part of the schema.
    assert validate_object(_canonical(obj)) == []
    # created_at is stamped at the API boundary (ADR-0016).
    assert obj["provenance"]["created_at"] is not None


def test_generate_surfaces_available_ops_hint():
    # The API attaches the engine's authoritative available_ops set (KAN-243),
    # so the web drives edit-button visibility from it, not a client heuristic.
    ratio = client.post(
        "/generate", json={"blueprint_code": "ratio_medium", "seed": 42, "count": 1}
    ).json()["questions"][0]
    assert isinstance(ratio["available_ops"], list)
    # Sorted for stable, JSON-friendly output.
    assert ratio["available_ops"] == sorted(ratio["available_ops"])
    # A ratio aid bar model is toggleable...
    assert "toggle-diagram" in ratio["available_ops"]

    # ...but a geometry mandatory figure is not.
    geo = client.post(
        "/generate", json={"blueprint_code": "geometry_area_hard", "seed": 7, "count": 1}
    ).json()["questions"][0]
    assert "toggle-diagram" not in geo["available_ops"]


def test_generate_count_returns_unique_batch():
    resp = client.post(
        "/generate", json={"blueprint_code": "ratio_medium", "seed": 1000, "count": 3}
    )
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
