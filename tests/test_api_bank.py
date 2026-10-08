"""W1d — GET /bank (owner-scoped) and POST /render/question + assets."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.main import app
from exam_engine import generate
from exam_engine.bank import open_bank
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
    bank = open_bank(owner_id=owner)
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
    bank = open_bank(owner_id="alice")
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
