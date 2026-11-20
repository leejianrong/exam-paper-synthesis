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


# --- W1a: set-cosmetic + editable-slot discovery ------------------------------


def test_edit_set_cosmetic_renames_and_stamps_lineage():
    source = _generate("ratio_medium", 42)
    resp = client.post(
        "/edit/set-cosmetic",
        json={"question": source, "changes": {"names": ["Ann", "Ben", "Cal"]}},
    )
    assert resp.status_code == 200
    child = resp.json()["question"]
    assert validate_object(_canonical(child)) == []
    assert child["parameters"]["names"] == ["Ann", "Ben", "Cal"]
    assert child["question"]["parts"][0]["answer"] == source["question"]["parts"][0]["answer"]
    assert child["provenance"]["parent_id"] == source["id"]
    assert child["provenance"]["created_at"] is not None
    # Not a button op: the available_ops hint stays the one-click set.
    assert "set-cosmetic" not in child["available_ops"]


def test_edit_set_cosmetic_rejects_numeric_param_with_422():
    source = _generate("ratio_medium", 42)
    resp = client.post("/edit/set-cosmetic", json={"question": source, "changes": {"total": 99}})
    assert resp.status_code == 422
    assert "changes the maths" in resp.json()["detail"]


def test_edit_set_cosmetic_without_changes_is_422():
    source = _generate("ratio_medium", 42)
    resp = client.post("/edit/set-cosmetic", json={"question": source})
    assert resp.status_code == 422


def test_editable_params_endpoint():
    resp = client.get("/blueprints/ratio_medium/params")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "ratio_medium"
    assert body["slots"] == [{"key": "names", "role": "name", "count": 3, "max_length": 24}]
    assert client.get("/blueprints/geometry_angle_easy/params").json()["slots"] == []
    assert client.get("/blueprints/nope/params").status_code == 404


# --- EXA-89: set-numbers ---------------------------------------------------------


def test_edit_set_numbers_resolves_and_offers_itself_in_the_hint():
    source = _generate("ratio_easy", 3)
    assert "set-numbers" in source["available_ops"]  # the editor offers "Edit numbers…"
    resp = client.post(
        "/edit/set-numbers",
        json={"question": source, "changes": {"ratio": [3, 4], "total": 140}},
    )
    assert resp.status_code == 200
    child = resp.json()["question"]
    assert validate_object(_canonical(child)) == []
    assert child["question"]["parts"][0]["answer"]["value"] == 80
    assert child["parameters"]["names"] == source["parameters"]["names"]
    assert child["provenance"]["parent_id"] == source["id"]
    assert child["provenance"]["created_at"] is not None


def test_edit_set_numbers_refusal_is_a_plain_sentence():
    source = _generate("ratio_easy", 3)
    resp = client.post("/edit/set-numbers", json={"question": source, "changes": {"total": 301}})
    assert resp.status_code == 422
    assert resp.json()["detail"].startswith("The amount must be a multiple of 12:")


def test_set_numbers_not_offered_without_free_numbers():
    assert "set-numbers" not in _generate("ratio_hard", 1)["available_ops"]
    source = _generate("ratio_hard", 1)
    resp = client.post("/edit/set-numbers", json={"question": source, "changes": {"spent": 10}})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "The numbers in this question can't be changed."


def test_set_numbers_on_tampered_parameters_is_a_422_not_a_500():
    source = _generate("ratio_easy", 3)
    source["parameters"]["ratio"] = 5
    resp = client.post("/edit/set-numbers", json={"question": source, "changes": {"ratio": [1, 2]}})
    assert resp.status_code == 422
    assert resp.json()["detail"].startswith("This question's numbers don't fit")


def test_editable_params_endpoint_lists_free_numbers():
    body = client.get("/blueprints/ratio_easy/params").json()
    assert body["numbers"] == [
        {"key": "ratio", "label": "Ratio", "list": True, "minimum": 1, "maximum": 9, "sep": ":"},
        {
            "key": "total",
            "label": "Amount shared ($)",
            "list": False,
            "minimum": 6,
            "maximum": 2000,
        },
    ]
    assert client.get("/blueprints/ratio_hard/params").json()["numbers"] == []
