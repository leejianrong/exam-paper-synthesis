"""W1d — GET /bank (owner-scoped) and POST /render/question + assets."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.bankstore import open_owner_bank
from app.main import app
from exam_engine import generate
from fastapi.testclient import TestClient

client = TestClient(app)
SOURCED = Path(__file__).parent / "fixtures" / "sourced"
ALICE = {"X-Dev-Owner": "alice"}
BOB = {"X-Dev-Owner": "bob"}


def _fixture(name: str) -> dict:
    return json.loads((SOURCED / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")
    monkeypatch.setenv("EXAM_BANK_PATH", str(tmp_path / "bank.sqlite3"))


def _seed(owner: str, *objs: dict) -> None:
    bank = open_owner_bank(owner)
    for obj in objs:
        bank.add(obj)
    bank.close()


def test_bank_requires_auth(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert client.get("/bank", headers=ALICE).status_code == 401


def test_bank_lists_only_the_owners_questions():
    mcq, table = _fixture("psle_2023_mcq"), _fixture("psle_2023_table")
    _seed("alice", mcq, table)
    _seed("bob", _fixture("psle_2023_ratio"))

    items = client.get("/bank", headers=ALICE).json()["items"]
    assert [i["id"] for i in items] == [mcq["id"], table["id"]]
    first = items[0]
    assert first["question"]["id"] == mcq["id"] and first["source_type"] == "sourced"
    assert first["reviewed"] is False and first["level"] and first["topic"]
    assert [i["id"] for i in client.get("/bank", headers=BOB).json()["items"]] == [
        _fixture("psle_2023_ratio")["id"]
    ]
    assert client.get("/bank", headers={"X-Dev-Owner": "carol"}).json()["items"] == []


def test_default_owner_sees_what_the_cli_imported():
    """The CLI writes as the `local` owner; the dev stub defaults to it."""
    _seed("local", _fixture("psle_2023_mcq"))
    assert len(client.get("/bank").json()["items"]) == 1


def test_bank_filters_and_review_flag():
    mcq = _fixture("psle_2023_mcq")
    _seed("alice", mcq, generate("ratio_medium", 1))
    bank = open_owner_bank("alice")
    bank.mark_reviewed(mcq["id"])
    bank.close()

    sourced = client.get("/bank?source_type=sourced", headers=ALICE).json()["items"]
    assert [i["id"] for i in sourced] == [mcq["id"]] and sourced[0]["reviewed"] is True
    generated = client.get("/bank?source_type=generated", headers=ALICE).json()["items"]
    assert len(generated) == 1 and generated[0]["reviewed"] is False
    assert len(client.get("/bank?reviewed=true", headers=ALICE).json()["items"]) == 1


def test_render_fragment_student_and_key_for_every_question_shape():
    for name in ("mcq", "table", "grid_net", "construction", "stem_diagram", "ratio"):
        q = _fixture(f"psle_2023_{name}")
        student = client.post("/render/question", json={"question": q})
        assert student.status_code == 200, name
        html = student.json()["html"]
        assert html.startswith('<div class="frag unnumbered">') and "<html" not in html
        assert "Answer:" not in html and 'class="solution"' not in html

        key = client.post("/render/question", json={"question": q, "mode": "key", "number": 4})
        khtml = key.json()["html"]
        assert 'style="counter-reset: q 3"' in khtml, name
        assert 'class="solution"' in khtml, name


def test_render_fragment_strips_ui_hints_and_rejects_invalid():
    q = generate("ratio_medium", 1)
    q["available_ops"] = ["regenerate"]
    assert client.post("/render/question", json={"question": q}).status_code == 200
    bad = generate("ratio_medium", 1)
    del bad["question"]["total_marks"]
    assert client.post("/render/question", json={"question": bad}).status_code == 422
    assert (
        client.post("/render/question", json={"question": q, "mode": "teacher"}).status_code == 422
    )


def test_fragment_assets_are_cacheable_and_scoped_for_a_shadow_root():
    css = client.get("/render/question.css")
    assert css.status_code == 200 and css.headers["content-type"].startswith("text/css")
    assert "max-age" in css.headers["cache-control"]
    assert ":host {" in css.text and ":root {" not in css.text
    assert "@font-face" in css.text and ".katex" in css.text

    js = client.get("/render/katex.js")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    assert "renderMathInElement" in js.text and "katex" in js.text


# --- POST /bank/import (W2c) -----------------------------------------------------------


def _import(objects, *, replace=False, headers=ALICE):
    return client.post(
        "/bank/import", json={"objects": objects, "replace": replace}, headers=headers
    )


def test_import_stores_unreviewed_even_if_the_file_claims_review():
    mcq = _fixture("psle_2023_mcq")
    mcq.setdefault("validation", {}).setdefault("checks", {})["human_reviewed"] = True
    resp = _import([mcq, _fixture("psle_2023_table")])
    assert resp.status_code == 200
    body = resp.json()
    assert (body["imported"], body["invalid"], body["duplicate"]) == (2, 0, 0)
    assert [r["status"] for r in body["results"]] == ["imported", "imported"]
    items = client.get("/bank", headers=ALICE).json()["items"]
    assert [i["reviewed"] for i in items] == [False, False]


def test_one_bad_item_never_blocks_the_rest_and_errors_are_path_pointed():
    good = _fixture("psle_2023_ratio")
    broken = _fixture("psle_2023_mcq")
    del broken["question"]["total_marks"]
    body = _import([broken, "not an object", good]).json()
    assert [r["status"] for r in body["results"]] == ["invalid", "invalid", "imported"]
    assert any("total_marks" in e for e in body["results"][0]["errors"])
    assert body["results"][1]["errors"] == ["<root>: must be an object"]
    assert body["results"][0]["id"] == broken["id"]
    assert [i["id"] for i in client.get("/bank", headers=ALICE).json()["items"]] == [good["id"]]


def test_duplicates_report_unless_replace_is_ticked():
    mcq = _fixture("psle_2023_mcq")
    assert _import([mcq]).json()["imported"] == 1
    again = _import([mcq]).json()
    assert again["duplicate"] == 1 and again["results"][0]["status"] == "duplicate"
    edited = {**mcq, "question": {**mcq["question"], "stem": "A new stem."}}
    replaced = _import([edited], replace=True).json()
    assert replaced["replaced"] == 1 and replaced["results"][0]["status"] == "replaced"
    stored = client.get("/bank", headers=ALICE).json()["items"][0]["question"]
    assert stored["question"]["stem"] == "A new stem."
    # a duplicate inside one request is reported the same way
    twin = _fixture("psle_2023_table")
    assert [r["status"] for r in _import([twin, twin]).json()["results"]] == [
        "imported",
        "duplicate",
    ]


def test_import_is_owner_scoped():
    mcq = _fixture("psle_2023_mcq")
    assert _import([mcq], headers=BOB).json()["imported"] == 1
    assert client.get("/bank", headers=ALICE).json()["items"] == []
    assert _import([mcq], headers=ALICE).json()["imported"] == 1  # alice has her own copy


def test_import_limits(monkeypatch):
    objs = [_fixture("psle_2023_mcq")] * 201
    assert _import(objs).status_code == 422
    monkeypatch.setattr("app.routes_bank.MAX_IMPORT_BYTES", 500)
    assert _import([_fixture("psle_2023_mcq")]).status_code == 413


def test_import_rejects_malformed_requests_and_needs_auth(monkeypatch):
    assert client.post("/bank/import", content=b"{nope", headers=ALICE).status_code == 422
    assert client.post("/bank/import", json={"objects": "x"}, headers=ALICE).status_code == 422
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert _import([]).status_code == 401


# --- review toggle (ADR-0019: a deliberate act, owner-scoped, sourced only) ----------------


def _review(obj_id: str, reviewed: bool, headers=ALICE):
    return client.put(f"/bank/{obj_id}/review", json={"reviewed": reviewed}, headers=headers)


def test_review_toggle_marks_and_withdraws_and_shows_in_the_listing():
    mcq = _fixture("psle_2023_mcq")
    client.post("/bank/import", json={"objects": [mcq]}, headers=ALICE)
    item = lambda: client.get("/bank", headers=ALICE).json()["items"][0]  # noqa: E731
    assert item()["reviewed"] is False  # imports arrive unreviewed

    assert _review(mcq["id"], True).json() == {"id": mcq["id"], "reviewed": True}
    assert item()["reviewed"] is True
    assert client.get("/bank?reviewed=true", headers=ALICE).json()["items"]
    assert _review(mcq["id"], True).status_code == 200  # idempotent

    assert _review(mcq["id"], False).json()["reviewed"] is False
    assert item()["reviewed"] is False


def test_review_is_owner_scoped_and_needs_auth(monkeypatch):
    mcq = _fixture("psle_2023_mcq")
    client.post("/bank/import", json={"objects": [mcq]}, headers=ALICE)
    assert _review(mcq["id"], True, BOB).status_code == 404  # not Bob's, whatever the id
    assert client.get("/bank", headers=ALICE).json()["items"][0]["reviewed"] is False
    assert _review("sourced:nope", True).status_code == 404
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert _review(mcq["id"], True).status_code == 401


def test_replacing_a_reviewed_question_resets_review():
    mcq = _fixture("psle_2023_mcq")
    client.post("/bank/import", json={"objects": [mcq]}, headers=ALICE)
    _review(mcq["id"], True)
    client.post("/bank/import", json={"objects": [mcq], "replace": True}, headers=ALICE)
    assert client.get("/bank", headers=ALICE).json()["items"][0]["reviewed"] is False


def test_generated_questions_are_not_part_of_the_review_gate():
    obj = generate("ratio_medium", 3)
    bank = open_owner_bank("alice")
    bank.add(obj)
    bank.close()
    resp = _review(obj["id"], True)
    assert resp.status_code == 422 and "sourced" in resp.json()["detail"]


def test_render_fragment_draws_charts_server_side_and_rejects_inconsistent_ones():
    """T1: a chart goes through the same engine markup as the PDF (no TS mirror), and
    the hidden pie value never reaches the student fragment's text."""
    from pathlib import Path

    from exam_engine.chart import leaked_hidden_values

    sourced = Path(__file__).parent / "fixtures" / "sourced"
    for kind in ("pie", "bar", "line"):
        q = json.loads((sourced / f"standin_chart_{kind}.json").read_text("utf-8"))
        html = client.post("/render/question", json={"question": q}).json()["html"]
        assert '<figure class="diagram"><svg' in html, kind
        if kind == "pie":
            assert leaked_hidden_values(q["question"]["diagram"], html) == []

    bad = json.loads((sourced / "standin_chart_bar.json").read_text("utf-8"))
    bad["question"]["diagram"]["series"][0]["values"][0] = 99
    resp = client.post("/render/question", json={"question": bad})
    assert resp.status_code == 422 and "values_within_axis" in resp.text


def test_render_fragment_draws_solids_server_side_and_rejects_inconsistent_ones():
    """T2: a solid goes through the same engine markup as the PDF; a hidden dimension
    never reaches the student fragment's text."""
    from exam_engine.solid import leaked_hidden_values

    sourced = Path(__file__).parent / "fixtures" / "sourced"
    for name in ("tank", "cuboid", "level"):
        q = json.loads((sourced / f"standin_solid_{name}.json").read_text("utf-8"))
        html = client.post("/render/question", json={"question": q}).json()["html"]
        assert '<figure class="diagram"><svg' in html, name
        assert leaked_hidden_values(q["question"]["diagram"], html) == [], name

    bad = json.loads((sourced / "standin_solid_tank.json").read_text("utf-8"))
    bad["question"]["diagram"]["fill"]["height"] = 99
    resp = client.post("/render/question", json={"question": bad})
    assert resp.status_code == 422 and "fill_within_height" in resp.text


def test_render_fragment_draws_number_lines_server_side():
    sourced = Path(__file__).parent / "fixtures" / "sourced"
    for name in ("fraction", "decimal"):
        q = json.loads((sourced / f"standin_numberline_{name}.json").read_text("utf-8"))
        html = client.post("/render/question", json={"question": q}).json()["html"]
        assert '<figure class="diagram"><svg' in html, name
    bad = json.loads((sourced / "standin_numberline_decimal.json").read_text("utf-8"))
    bad["question"]["diagram"]["marked_points"][0]["at"] = 0.5
    resp = client.post("/render/question", json={"question": bad})
    assert resp.status_code == 422 and "unknown_points_not_on_labelled_ticks" in resp.text


def test_render_fragment_draws_panels_server_side():
    sourced = Path(__file__).parent / "fixtures" / "sourced"
    q = json.loads((sourced / "standin_panels_before_after.json").read_text("utf-8"))
    html = client.post("/render/question", json={"question": q}).json()["html"]
    assert '<figure class="diagram"><svg' in html and "Before" in html
    q["question"]["diagram"]["panels"][1]["figure"]["fill"]["height"] = 99
    resp = client.post("/render/question", json={"question": q})
    assert resp.status_code == 422 and "panel2_fill_within_height" in resp.text


def test_render_fragment_prints_expression_answers_and_rejects_uncollected_ones():
    sourced = Path(__file__).parent / "fixtures" / "sourced"
    q = json.loads((sourced / "standin_expression_pi.json").read_text("utf-8"))
    html = client.post("/render/question", json={"question": q, "mode": "key"}).json()["html"]
    assert r"\left(42\pi + 84\right)" in html and "Answer:" in html
    q["question"]["parts"][0]["answer"]["terms"].reverse()
    resp = client.post("/render/question", json={"question": q})
    assert resp.status_code == 422 and "terms_in_canonical_order" in resp.text
