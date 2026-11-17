"""P8a — GET /papers, POST /documents with a template, POST /documents/generate."""

from __future__ import annotations

import pytest
from app.main import app
from app.ops import strip_document_hints
from exam_engine.document import paper_outline, validate_document
from exam_engine.paper import generate_paper
from fastapi.testclient import TestClient

client = TestClient(app)
ALICE = {"X-Dev-Owner": "alice"}
BOB = {"X-Dev-Owner": "bob"}


@pytest.fixture(autouse=True)
def _dev_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")
    monkeypatch.setenv("EXAM_DOCS_PATH", str(tmp_path / "docs.sqlite3"))


def test_paper_templates_are_listed_in_order():
    body = client.get("/papers").json()
    assert [t["code"] for t in body["templates"]] == ["p1_booklet_a", "p1_booklet_b", "p2"]
    assert [t["label"] for t in body["templates"]] == [
        "Paper 1 · Booklet A",
        "Paper 1 · Booklet B",
        "Paper 2",
    ]
    p2 = body["templates"][2]
    assert p2["time_min"] == 90
    assert [(s["title"], s["mode"], s["marks_target"]) for s in p2["sections"]] == [
        ("Section A", "short", 10),
        ("Section B", "structured", 45),
    ]
    assert body["levels"] == ["P5", "P6"]


def test_a_document_can_start_from_a_template():
    rec = client.post("/documents", json={"template": "p2"}, headers=ALICE).json()
    blocks = rec["document"]["content"]["content"]
    assert rec["title"] == "Paper 2"
    cover, back, *sections = blocks
    assert cover["type"] == "coverPage" and cover["attrs"]["paper"] == "Paper 2"
    assert back["type"] == "blankPage"  # the blank back of the cover (EXA-140)
    assert "level" not in cover["attrs"]  # left for the teacher
    assert [b["attrs"]["title"] for b in sections] == ["Section A", "Section B"]
    assert rec["document"]["settings"] == {"time_min": 90}
    named = client.post("/documents", json={"template": "p2", "title": "Mock"}, headers=ALICE)
    assert named.json()["title"] == "Mock"
    assert client.post("/documents", json={"template": "nope"}).status_code == 404


def test_generate_creates_a_valid_owned_paper_with_a_report():
    resp = client.post(
        "/documents/generate", json={"template": "p2", "level": "P6", "seed": 5}, headers=ALICE
    )
    assert resp.status_code == 201
    rec = resp.json()
    doc = rec["document"]
    assert rec["title"] == "P6 Paper 2"
    # the stored document is the engine's paper for that seed, with created_at stamped
    expected, report = generate_paper("p2", "P6", 5)
    assert rec["report"] == report
    assert len(doc["content"]["content"]) == len(expected["content"]["content"])
    stamped = [
        n["attrs"]["question"]["provenance"]["created_at"]
        for n in doc["content"]["content"]
        if n["type"] == "templatedQuestion"
    ]
    assert stamped and all(stamped)
    # editor hints are attached on the way out, as for GET /documents/{id}
    assert all(
        "available_ops" in n["attrs"]["question"]
        for n in doc["content"]["content"]
        if n["type"] == "templatedQuestion"
    )
    assert [s["marks"] for s in paper_outline(doc)] == [10, 45]

    # it is Alice's: listed for her, invisible to Bob, and it round-trips through save
    assert any(
        d["id"] == rec["id"] for d in client.get("/documents", headers=ALICE).json()["documents"]
    )
    assert client.get(f"/documents/{rec['id']}", headers=BOB).status_code == 404
    got = client.get(f"/documents/{rec['id']}", headers=ALICE).json()
    saved = client.put(
        f"/documents/{rec['id']}",
        json={"document": got["document"], "base_version": got["version"]},
        headers=ALICE,
    )
    assert saved.status_code == 200
    stored = client.get(f"/documents/{rec['id']}", headers=ALICE).json()["document"]
    assert validate_document(strip_document_hints(stored)) == []


def test_generate_one_paper_of_a_set_passes_the_sets_topics_to_the_engine():
    """EXA-153: the wizard sends the topics of the set's papers made so far."""
    so_far = {"Volume": 3, "Rate": 2}
    resp = client.post(
        "/documents/generate",
        json={"template": "p2", "level": "P6", "seed": 5, "set_topics": so_far},
        headers=ALICE,
    )
    assert resp.status_code == 201
    assert resp.json()["report"] == generate_paper("p2", "P6", 5, so_far)[1]
    assert resp.json()["report"] != generate_paper("p2", "P6", 5)[1]
    for bad in ({"Volume": -1}, {"x" * 101: 1}, {f"t{i}": 1 for i in range(101)}):
        assert (
            client.post(
                "/documents/generate",
                json={"template": "p2", "seed": 5, "set_topics": bad},
                headers=ALICE,
            ).status_code
            == 422
        ), bad


def test_generate_without_a_seed_picks_one_and_rejects_bad_input():
    a = client.post("/documents/generate", json={"template": "p1_booklet_b"}, headers=ALICE)
    assert a.status_code == 201 and a.json()["report"]["level"] == "P6"
    assert 1 <= a.json()["report"]["seed"] < 2**31
    assert client.post("/documents/generate", json={"template": "p9"}).status_code == 404
    assert (
        client.post("/documents/generate", json={"template": "p2", "level": "P4"}).status_code
        == 422
    )


def test_generate_needs_an_identity(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert client.post("/documents/generate", json={"template": "p2"}).status_code == 401


def _write(node: dict, text: str) -> None:
    node["content"] = [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]


def test_export_refuses_empty_placeholders_unless_told_to_print_anyway(monkeypatch):
    """EXA-137: a generated paper with unwritten placeholders never prints by accident."""
    from app import routes_documents

    monkeypatch.setattr(routes_documents.export, "html_to_pdf", lambda html: b"%PDF-1.7 fake")
    charged: list[str] = []
    monkeypatch.setattr(routes_documents, "check_export_quota", charged.append)
    gen = client.post(
        "/documents/generate",
        json={"template": "p2", "level": "P5", "seed": 1},
        headers=ALICE,
    ).json()
    assert gen["report"]["placeholders"] == 3  # today's content: P5 Paper 2 Section B is short
    url = f"/documents/{gen['id']}/export"

    for mode in ("student", "key", "full"):
        resp = client.post(f"{url}/{mode}", headers=ALICE)
        assert resp.status_code == 409, mode
        detail = resp.json()["detail"]
        assert detail["code"] == "unfilled_placeholders"
        assert detail["questions"] == [18, 19, 20]  # the last structured slots
        assert "Questions 18, 19, 20 are still empty" in detail["message"]
    assert charged == []  # refused before any export allowance is spent

    ok = client.post(f"{url}/student?allow_placeholders=true", headers=ALICE)
    assert ok.status_code == 200 and ok.content.startswith(b"%PDF")
    assert charged == ["alice"]
    # the in-app preview still shows the paper as it is (the editor flags the gaps)
    assert client.get(f"/documents/{gen['id']}/preview/student", headers=ALICE).status_code == 200

    # once the teacher writes one, only the others are listed; once all, it prints
    doc = strip_document_hints(gen["document"])
    phs = [
        n
        for n in doc["content"]["content"]
        if (n.get("attrs") or {}).get("slot", {}).get("placeholder")
    ]
    _write(phs[0], "What is 1 + 1?")
    saved = client.put(
        f"/documents/{gen['id']}",
        json={"document": doc, "base_version": gen["version"]},
        headers=ALICE,
    ).json()
    one = client.post(f"{url}/student", headers=ALICE).json()["detail"]
    assert one["questions"] == [19, 20] and "Questions 19, 20 are still empty" in one["message"]
    _write(phs[1], "And 2 + 2?")
    _write(phs[2], "And 3 + 3?")
    resp = client.put(
        f"/documents/{gen['id']}",
        json={"document": doc, "base_version": saved["version"]},
        headers=ALICE,
    )
    assert resp.status_code == 200
    assert client.post(f"{url}/student", headers=ALICE).status_code == 200
