"""EXA-90 — POST /bank/own (save a teacher's own question) and GET /bank/topics.

Named ``test_api_*`` so it also runs on Postgres with ``EXAM_TEST_BACKEND=postgres``.
"""

from __future__ import annotations

from app.main import app
from documents import freeform_block, image_node, make_doc, multipart_block, part_node
from fastapi.testclient import TestClient
from images import png

client = TestClient(app)
ALICE = {"X-Dev-Owner": "alice"}
BOB = {"X-Dev-Owner": "bob"}


def _env(monkeypatch):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")


def _upload(headers=ALICE) -> str:
    resp = client.post("/assets", content=png(), headers={**headers, "Content-Type": "image/png"})
    assert resp.status_code == 201
    return resp.json()["id"]


def _block(asset_id: str | None = None) -> dict:
    block = multipart_block(
        part_node("How many litres?", marks=2, answer="45", ans_unit="ℓ"),
        part_node("How many more?", marks=1, answer="15"),
        stem="Sample Primary has a tank.",
        block_id="ffm_api1",
    )
    if asset_id:
        block["content"].insert(1, image_node(asset_id))
    return block


def _save(block: dict, headers=ALICE, **kw):
    body = {"block": block, "topic": "Volume", "level": "P5", **kw}
    return client.post("/bank/own", json=body, headers=headers)


def test_topics_list(monkeypatch):
    _env(monkeypatch)
    topics = client.get("/bank/topics").json()["topics"]
    assert {"topic": "Ratio", "strand": "Ratio"} in topics


def test_save_lists_it_unreviewed_and_owner_scoped(monkeypatch):
    _env(monkeypatch)
    resp = _save(_block(_upload()))
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "saved" and body["id"] == "own-ffm_api1"
    assert body["reviewed"] is False and body["source_type"] == "sourced"
    items = client.get("/bank", headers=ALICE).json()["items"]
    assert [i["id"] for i in items] == ["own-ffm_api1"]
    assert items[0]["question"]["provenance"]["created_by"] == "teacher"
    assert items[0]["question"]["freeform"]["content"][2]["type"] == "freeformPart"
    assert client.get("/bank", headers=BOB).json()["items"] == []


def test_duplicate_is_reported_and_replace_updates_it(monkeypatch):
    _env(monkeypatch)
    block = _block()
    assert _save(block).status_code == 200
    again = _save(block)
    assert again.status_code == 409 and "already in your bank" in again.json()["detail"]
    block["content"][0]["content"][0]["text"] = "Example Primary has a tank."
    replaced = _save(block, replace=True, level="P6")
    assert replaced.status_code == 200 and replaced.json()["status"] == "replaced"
    (item,) = client.get("/bank", headers=ALICE).json()["items"]
    assert item["level"] == "P6" and item["question"]["question"]["stem"].startswith("Example")
    # bob saving a block with the same id has his own copy
    assert _save(block, headers=BOB).json()["status"] == "saved"


def test_someone_elses_image_is_refused_on_save_and_on_import(monkeypatch):
    _env(monkeypatch)
    bobs = _upload(BOB)
    resp = _save(_block(bobs))
    assert resp.status_code == 422 and bobs in str(resp.json()["detail"])
    # the same question, saved by bob, can't be imported into alice's bank either
    obj = _save(_block(bobs), headers=BOB).json()["question"]
    body = client.post("/bank/import", json={"objects": [obj]}, headers=ALICE).json()
    assert body["invalid"] == 1 and bobs in body["results"][0]["errors"][0]


def test_unsavable_blocks_are_422(monkeypatch):
    _env(monkeypatch)
    empty = freeform_block("", marks=2)
    empty["content"] = [{"type": "paragraph"}]
    assert "Write the question" in _save(empty).json()["detail"]
    assert _save(freeform_block("Hi", marks=None)).status_code == 422
    assert _save(freeform_block("Hi", marks=1), topic="Cookery").status_code == 422
    assert _save(freeform_block("Hi", marks=1), level="P4").status_code == 422
    unmarked = _save(freeform_block("Hi", marks=None, block_id="ff_m1"), marks=2)
    assert (
        unmarked.status_code == 200 and unmarked.json()["question"]["question"]["total_marks"] == 2
    )


def test_needs_auth(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH", raising=False)
    assert _save(_block()).status_code == 401


def test_inserted_into_another_paper_prints_the_same(monkeypatch):
    """Saved from one paper, inserted into another by the same owner: the image still draws
    and the printed key matches the original paper's."""
    _env(monkeypatch)
    block = _block(_upload())
    obj = _save(block).json()["question"]
    papers = []
    for content in (
        block,
        {**obj["freeform"], "attrs": {**obj["freeform"]["attrs"], "bank_id": obj["id"]}},
    ):
        rec = client.post("/documents", json={"title": "Paper"}, headers=ALICE).json()
        saved = client.put(
            f"/documents/{rec['id']}",
            json={"document": make_doc(content, title="Paper"), "base_version": rec["version"]},
            headers=ALICE,
        )
        assert saved.status_code == 200, saved.text
        papers.append(client.get(f"/documents/{rec['id']}/preview/full", headers=ALICE).text)
    assert papers[0] == papers[1] and "data:image/png;base64" in papers[0]
