"""EXA-169 — defaults for new papers: the account's school name, level and marks placement (and
the key style, EXA-159) are written into every new paper at creation, server-side, on every
creation route. An empty setting changes nothing; saved papers are never touched."""

from __future__ import annotations

import pytest
from app.main import app
from app.ops import strip_document_hints
from exam_engine import paper
from exam_engine.document import validate_document
from fastapi.testclient import TestClient

client = TestClient(app)
ALICE = {"X-Dev-Owner": "alice"}
SCHOOL = "Example Primary School"
SET = ("p2", "p1_booklet_b", "p1_booklet_a")  # the wizard's fill order (EXA-153)


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")
    monkeypatch.setenv("EXAM_DOCS_PATH", str(tmp_path / "docs.sqlite3"))
    monkeypatch.setenv("EXAM_BANK_PATH", str(tmp_path / "bank.sqlite3"))


def _set(**patch) -> None:
    resp = client.put("/settings", json=patch, headers=ALICE)
    assert resp.status_code == 200, resp.text


def _new(json: dict) -> dict:
    resp = client.post("/documents", json=json, headers=ALICE)
    assert resp.status_code == 201, resp.text
    return resp.json()["document"]


def _generate(json: dict) -> tuple[dict, dict]:
    resp = client.post("/documents/generate", json={"seed": 5, **json}, headers=ALICE)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["document"], body["report"]


def _cover(doc: dict) -> dict:
    first = doc["content"]["content"][0]
    assert first["type"] == "coverPage"
    return first["attrs"]


def _make_set(level: str | None = None) -> list[tuple[dict, dict]]:
    """An exam set as the New dialog makes it: three generate calls, each told the topics of
    the papers made before it."""
    out, topics = [], {}
    for code in SET:
        body = {"template": code, "set_topics": topics, **({"level": level} if level else {})}
        doc, report = _generate(body)
        for t, n in report["topics"].items():
            topics[t] = topics.get(t, 0) + n
        out.append((doc, report))
    return out


def test_empty_defaults_change_nothing():
    """The default settings make the papers made before EXA-169."""
    blank = _new({"title": "Blank"})
    assert "marks_placement" not in blank["settings"]  # absent prints after the Ans: line
    assert blank["content"]["content"] == []

    starter = _new({"template": "p2"})
    expected = paper.template_document("p2")
    assert starter["content"] == expected["content"]  # no school, no level on the cover
    assert "level" not in _cover(starter) and "school" not in _cover(starter)

    generated, report = _generate({"template": "p1_booklet_a"})
    assert report["level"] == "P6"  # P6 when neither the request nor the account says
    assert _cover(generated)["level"] == "Primary 6"
    assert "school" not in _cover(generated)


def test_every_creation_route_takes_the_defaults():
    _set(school_name=SCHOOL, default_level="P5", marks_placement="both", answer_key_style="worked")

    blank = _new({"title": "Blank"})  # no cover to name a school on
    assert blank["settings"]["marks_placement"] == "both"
    assert blank["settings"]["key_options"]["layout"] == "full"

    starter = _new({"template": "p1_booklet_b"})
    assert _cover(starter)["school"] == SCHOOL
    assert _cover(starter)["level"] == "Primary 5"
    assert starter["settings"]["marks_placement"] == "both"
    assert starter["settings"]["key_options"]["layout"] == "full"
    assert starter["settings"]["number_from"] == 16  # the template's own settings stay

    single, report = _generate({"template": "p1_booklet_b"})
    assert report["level"] == "P5"
    assert single["title"].startswith("P5 ")
    assert _cover(single)["school"] == SCHOOL
    assert _cover(single)["level"] == "Primary 5"
    assert single["settings"]["marks_placement"] == "both"
    for node in single["content"]["content"]:
        if node["type"] == "templatedQuestion":
            assert node["attrs"]["question"]["syllabus"]["level"] == "P5"

    for doc, report in _make_set():
        assert report["level"] == "P5"
        assert _cover(doc)["school"] == SCHOOL
        assert _cover(doc)["level"] == "Primary 5"
        assert doc["settings"]["marks_placement"] == "both"
        assert doc["settings"]["key_options"]["layout"] == "full"
        assert validate_document(strip_document_hints(doc)) == []


def test_an_explicit_level_beats_the_default():
    _set(school_name=SCHOOL, default_level="P5")
    single, report = _generate({"template": "p2", "level": "P6"})
    assert report["level"] == "P6"
    assert _cover(single)["level"] == "Primary 6"
    assert _cover(single)["school"] == SCHOOL
    for doc, report in _make_set("P6"):
        assert (report["level"], _cover(doc)["level"]) == ("P6", "Primary 6")


def test_saved_papers_keep_what_they_were_made_with():
    starter = client.post("/documents", json={"template": "p2"}, headers=ALICE).json()
    _set(school_name=SCHOOL, default_level="P6", marks_placement="question")
    again = client.get(f"/documents/{starter['id']}", headers=ALICE).json()["document"]
    assert again == starter["document"]
    assert "school" not in _cover(again)


def test_engine_defaults_are_plain_values():
    """The engine takes the values and fills only what is empty; it reads no settings."""
    doc = paper.template_document("p2", "P6")
    assert _cover(doc)["level"] == "Primary 6"
    named = paper.with_paper_defaults(doc, SCHOOL, "question")
    assert _cover(named)["school"] == SCHOOL
    assert named["settings"]["marks_placement"] == "question"
    assert "school" not in _cover(doc)  # the input is not changed
    _cover(doc)["school"] = "Another Example School"
    assert _cover(paper.with_paper_defaults(doc, SCHOOL))["school"] == "Another Example School"
    assert paper.with_paper_defaults(doc) == doc
    with pytest.raises(ValueError):
        paper.with_paper_defaults(doc, marks_placement="none")
    with pytest.raises(ValueError):
        paper.template_document("p2", "P4")
