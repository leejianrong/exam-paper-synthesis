"""EXA-168: the exam-set answer key of a folder (``/folders/{id}/key``), owner-scoped, with the
set found by ``paper_part`` and the export allowance spent like any other export. Runs on both
store backends (``EXAM_TEST_BACKEND=postgres`` moves every ``test_api_*`` module onto Postgres).
"""

from __future__ import annotations

import re

import pytest
from app import export
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
ALICE = {"X-Dev-Owner": "alice"}
BOB = {"X-Dev-Owner": "bob"}
SET = ["p1_booklet_a", "p1_booklet_b", "p2"]


@pytest.fixture(autouse=True)
def _dev_env(monkeypatch):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")
    monkeypatch.setenv("EXAM_EXPORT_LIMIT_PER_DAY", "2")
    monkeypatch.setenv("EXAM_EXPORT_LIMIT_PER_MINUTE", "0")


@pytest.fixture
def pdfs(monkeypatch):
    rendered: list[str] = []

    def render(html: str) -> bytes:
        rendered.append(html)
        return b"%PDF-set"

    monkeypatch.setattr(export, "html_to_pdf", render)
    return rendered


def _folder(name: str = "Term 3 Prelim", headers=ALICE) -> str:
    resp = client.post("/folders", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _generate(template: str, folder_id: str | None, seed: int = 5, headers=ALICE) -> dict:
    body = {"template": template, "level": "P6", "seed": seed, "folder_id": folder_id}
    resp = client.post("/documents/generate", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _set_folder(headers=ALICE, templates=SET) -> tuple[str, list[dict]]:
    folder = _folder(headers=headers)
    # made out of exam order, as the wizard makes them (Paper 2 first)
    made = {t: _generate(t, folder, headers=headers) for t in reversed(templates)}
    return folder, [made[t] for t in templates]


def _main(html: str) -> str:
    return html[html.index("<main ") : html.index("</main>")]


def test_the_set_key_needs_an_identity(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert client.post("/folders/x/key").status_code == 401
    assert client.get("/folders/x/key/preview").status_code == 401


def test_a_complete_set_prints_one_key_in_exam_order(pdfs):
    folder, papers = _set_folder()
    # another paper in the folder that is no part of a set is left out
    client.post("/documents", json={"title": "Spare worksheet", "folder_id": folder}, headers=ALICE)
    resp = client.post(f"/folders/{folder}/key", headers=ALICE)
    assert resp.status_code == 200, resp.text
    assert resp.content == b"%PDF-set"
    assert resp.headers["content-type"] == "application/pdf"
    assert 'filename="term-3-prelim-answer-key.pdf"' in resp.headers["content-disposition"]
    html = _main(pdfs[0])
    heads = re.findall(r'<h2 class="key-paper">([^<]*)</h2>', html)
    assert heads == ["Paper 1 Booklet A", "Paper 1 Booklet B", "Paper 2"]
    assert re.findall(r'data-part="(\w+)"', html) == ["booklet_a", "booklet_b", "paper_2"]
    preview = client.get(f"/folders/{folder}/key/preview", headers=ALICE)
    assert preview.status_code == 200
    assert _main(preview.text) == html  # the preview is the PDF's markup
    assert [p["paper_part"] for p in papers] == ["booklet_a", "booklet_b", "paper_2"]


def test_an_incomplete_set_is_a_409_before_any_export_is_spent(pdfs):
    folder, papers = _set_folder()
    client.delete(f"/documents/{papers[1]['id']}", headers=ALICE)
    resp = client.post(f"/folders/{folder}/key", headers=ALICE)
    assert resp.status_code == 409
    assert resp.json()["detail"] == {
        "code": "incomplete_set",
        "message": "This folder has no Booklet B. "
        "A set's answer key needs Booklet A, Booklet B and Paper 2.",
        "parts": ["booklet_b"],
    }
    assert client.get(f"/folders/{folder}/key/preview", headers=ALICE).status_code == 409
    assert pdfs == []
    assert client.get("/auth/quota", headers=ALICE).json()["left_day"] == 2


def test_two_booklet_as_are_ambiguous(pdfs):
    folder, _ = _set_folder()
    _generate("p1_booklet_a", folder, seed=9)
    resp = client.post(f"/folders/{folder}/key", headers=ALICE)
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["code"] == "ambiguous_set" and detail["parts"] == ["booklet_a"]
    assert detail["message"].startswith("This folder has more than one Booklet A.")
    assert pdfs == []


def test_another_owners_folder_is_a_404(pdfs):
    folder, _ = _set_folder()
    assert client.post(f"/folders/{folder}/key", headers=BOB).status_code == 404
    assert client.get(f"/folders/{folder}/key/preview", headers=BOB).status_code == 404
    assert client.post("/folders/nope/key", headers=ALICE).status_code == 404
    assert pdfs == []


def test_only_the_folders_own_papers_count(pdfs):
    folder = _folder()
    for t in SET[:2]:
        _generate(t, folder)
    _generate("p2", None)  # unfiled: not in the folder's set
    resp = client.post(f"/folders/{folder}/key", headers=ALICE)
    assert resp.status_code == 409 and resp.json()["detail"]["parts"] == ["paper_2"]


def test_empty_placeholders_are_refused_unless_asked(pdfs):
    folder, papers = _set_folder()
    rec = client.get(f"/documents/{papers[2]['id']}", headers=ALICE).json()
    doc = rec["document"]
    q = next(n for n in doc["content"]["content"] if n["type"] == "templatedQuestion")
    marks = q["attrs"]["question"]["question"]["total_marks"]
    place = {
        "type": "freeformQuestion",
        "attrs": {
            "block_id": "ff_placeholder",
            "marks": marks,
            "slot": {"marks": marks, "kind": "structured", "placeholder": True},
        },
        "content": [{"type": "paragraph"}],
    }
    at = doc["content"]["content"].index(q)
    doc["content"]["content"][at] = place
    saved = client.put(
        f"/documents/{rec['id']}",
        json={"document": doc, "base_version": rec["version"]},
        headers=ALICE,
    )
    assert saved.status_code == 200, saved.text
    resp = client.post(f"/folders/{folder}/key", headers=ALICE)
    assert resp.status_code == 409, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "unfilled_placeholders"
    assert detail["papers"] == [{"id": rec["id"], "part": "paper_2", "questions": [1]}]
    assert detail["message"] == (
        "Paper 2 question 1 is still empty. Write or fill it first, or download the key anyway."
    )
    assert pdfs == []
    anyway = client.post(f"/folders/{folder}/key?allow_placeholders=true", headers=ALICE)
    assert anyway.status_code == 200


def test_the_set_key_spends_the_allowance_then_429s(pdfs):
    folder, _ = _set_folder()
    url = f"/folders/{folder}/key"
    assert client.post(url, headers=ALICE).status_code == 200
    assert client.post(url, headers=ALICE).status_code == 200
    refused = client.post(url, headers=ALICE)
    assert refused.status_code == 429
    assert int(refused.headers["retry-after"]) > 0
    assert len(pdfs) == 2
    assert client.get(f"/folders/{folder}/key/preview", headers=ALICE).status_code == 200  # free


def test_a_failed_render_is_refunded(monkeypatch):
    folder, _ = _set_folder()

    def boom(html: str) -> bytes:
        raise RuntimeError("chromium crashed")

    monkeypatch.setattr(export, "html_to_pdf", boom)
    failing = TestClient(app, raise_server_exceptions=False)
    for _ in range(3):  # more failures than the allowance of 2
        assert failing.post(f"/folders/{folder}/key", headers=ALICE).status_code == 500
    assert client.get("/auth/quota", headers=ALICE).json()["left_day"] == 2
