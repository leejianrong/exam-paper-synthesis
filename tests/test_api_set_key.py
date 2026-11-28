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
    assert resp.headers["content-disposition"] == (
        'attachment; filename="term-3-prelim-answer-key.pdf"; '
        "filename*=UTF-8''Term%203%20Prelim%20answer%20key.pdf"
    )
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
    assert detail["message"] == (
        "Two papers titled \u201cP6 Paper 1 Booklet A\u201d both look like Booklet A. "
        "Keep one Booklet A in the folder to make the set's answer key."
    )
    assert pdfs == []


def _put(doc_id: str, change, headers=ALICE) -> None:
    rec = client.get(f"/documents/{doc_id}", headers=headers).json()
    doc = rec["document"]
    change(doc)
    saved = client.put(
        f"/documents/{doc_id}",
        json={"document": doc, "base_version": rec["version"]},
        headers=headers,
    )
    assert saved.status_code == 200, saved.text


def test_a_worksheet_titled_like_a_booklet_doesnt_block_the_set(pdfs):
    folder, papers = _set_folder()
    # no cover: its title is all that says "Booklet A", and the set's cover says more
    client.post(
        "/documents", json={"title": "Booklet A practice", "folder_id": folder}, headers=ALICE
    )
    listed = {d["title"]: d for d in client.get("/documents", headers=ALICE).json()["documents"]}
    assert listed["Booklet A practice"]["paper_part_source"] == "title"
    assert papers[0]["paper_part_source"] == "cover"
    resp = client.post(f"/folders/{folder}/key", headers=ALICE)
    assert resp.status_code == 200, resp.text
    assert len(pdfs) == 1


def test_a_renamed_booklet_is_still_found_by_its_cover(pdfs):
    folder, papers = _set_folder()
    # renamed to a title that names another part: the cover's paper line still decides
    _put(papers[0]["id"], lambda d: d.update(title="Booklet B notes"))
    assert client.post(f"/folders/{folder}/key", headers=ALICE).status_code == 200


@pytest.mark.parametrize(
    "field, values, message",
    [
        (
            "level",
            ("Primary 5", "Primary 6"),
            "Booklet A is Primary 5 but Booklet B is Primary 6.",
        ),
        (
            "school",
            ("Example Primary", "Sample Primary"),
            "Booklet A is from Example Primary but Booklet B is from Sample Primary.",
        ),
    ],
)
def test_a_mixed_set_is_a_409_naming_the_clash(pdfs, field, values, message):
    folder, papers = _set_folder()
    for paper, value in zip(papers, (values[0], values[1], values[1]), strict=True):
        _put(paper["id"], lambda d, v=value: d["content"]["content"][0]["attrs"].update({field: v}))
    resp = client.post(f"/folders/{folder}/key", headers=ALICE)
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["code"] == "mixed_set"
    assert detail["parts"] == ["booklet_a", "booklet_b"]
    assert (
        detail["message"] == f"{message} Make the covers match to print one answer key for the set."
    )
    assert client.get(f"/folders/{folder}/key/preview", headers=ALICE).status_code == 409
    assert pdfs == []


class _Racing:
    """The real store, but a paper changes between the folder's list and its read."""

    def __init__(self, store, change):
        self._store, self._change, self._done = store, change, False

    def __getattr__(self, name):
        return getattr(self._store, name)

    def get(self, owner, doc_id):
        if not self._done:
            self._done = True
            self._change(owner, doc_id)
        return self._store.get(owner, doc_id)


@pytest.mark.parametrize("race", ["deleted", "moved"])
def test_a_paper_gone_between_list_and_read_is_a_409_not_a_500(pdfs, race):
    from app.docstore import get_store

    folder, _ = _set_folder()
    other = _folder("Elsewhere")
    real = get_store()

    def change(owner, doc_id):
        if race == "deleted":
            real.delete(owner, doc_id)
        else:
            real.move(owner, doc_id, other)

    app.dependency_overrides[get_store] = lambda: _Racing(real, change)
    try:
        resp = TestClient(app, raise_server_exceptions=False).post(
            f"/folders/{folder}/key", headers=ALICE
        )
    finally:
        app.dependency_overrides.pop(get_store, None)
    assert resp.status_code == 409, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "incomplete_set" and detail["parts"] == ["booklet_a"]
    assert detail["message"].startswith("Booklet A was just deleted, moved or changed.")
    assert pdfs == []


def test_the_file_is_named_after_the_folder_in_any_script(pdfs):
    folder = _folder("Prélim 数学")
    for t in reversed(SET):
        _generate(t, folder)
    resp = client.post(f"/folders/{folder}/key", headers=ALICE)
    assert resp.status_code == 200
    assert resp.headers["content-disposition"] == (
        'attachment; filename="pr-lim-answer-key.pdf"; '
        "filename*=UTF-8''Pr%C3%A9lim%20%E6%95%B0%E5%AD%A6%20answer%20key.pdf"
    )


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
