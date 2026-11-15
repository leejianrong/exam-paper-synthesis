"""O2 — /folders API and moving papers (PATCH /documents/{id}): owner-scoped like documents."""

from __future__ import annotations

import io
import json
import os
import sqlite3
import zipfile

import pytest
from app.main import app
from documents import gen_block, make_doc, para
from exam_engine.document import empty_document
from fastapi.testclient import TestClient

client = TestClient(app)
ALICE = {"X-Dev-Owner": "alice"}
BOB = {"X-Dev-Owner": "bob"}


@pytest.fixture(autouse=True)
def _dev_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")
    monkeypatch.setenv("EXAM_DOCS_PATH", str(tmp_path / "docs.sqlite3"))
    monkeypatch.setenv("EXAM_BANK_PATH", str(tmp_path / "bank.sqlite3"))


def _folder(name: str = "Term 3", headers=ALICE) -> dict:
    resp = client.post("/folders", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _paper(headers=ALICE, **body) -> dict:
    resp = client.post("/documents", json={"title": "Paper", **body}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _folders(headers=ALICE) -> list[dict]:
    resp = client.get("/folders", headers=headers)
    assert resp.status_code == 200
    return resp.json()["folders"]


def _move(doc_id: str, folder_id: str | None, headers=ALICE):
    return client.patch(f"/documents/{doc_id}", json={"folder_id": folder_id}, headers=headers)


def _doc_ids(headers=ALICE) -> dict:
    return {
        d["id"]: d["folder_id"]
        for d in client.get("/documents", headers=headers).json()["documents"]
    }


def test_folder_routes_need_an_identity(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert client.get("/folders").status_code == 401
    assert client.post("/folders", json={"name": "x"}).status_code == 401
    assert client.patch("/folders/f", json={"name": "x"}).status_code == 401
    assert client.delete("/folders/f").status_code == 401
    assert client.patch("/documents/d", json={"folder_id": None}).status_code == 401


def test_crud():
    assert _folders() == []
    made = _folder("  Term 3 prelims ")
    assert set(made) == {"id", "name", "created_at", "updated_at", "papers"}
    assert made["name"] == "Term 3 prelims" and made["papers"] == 0
    _folder("Drafts")
    assert [f["name"] for f in _folders()] == ["Drafts", "Term 3 prelims"]

    resp = client.patch(f"/folders/{made['id']}", json={"name": "Prelims"}, headers=ALICE)
    assert resp.status_code == 200 and resp.json()["name"] == "Prelims"
    assert resp.json()["id"] == made["id"]

    assert client.delete(f"/folders/{made['id']}", headers=ALICE).status_code == 204
    assert [f["name"] for f in _folders()] == ["Drafts"]
    assert client.delete(f"/folders/{made['id']}", headers=ALICE).status_code == 404
    assert client.patch("/folders/nope", json={"name": "x"}, headers=ALICE).status_code == 404


@pytest.mark.parametrize("body", [{}, {"name": ""}, {"name": "   "}, {"name": "x" * 81}])
def test_bad_names_are_refused(body):
    assert client.post("/folders", json=body, headers=ALICE).status_code == 422
    f = _folder()
    assert client.patch(f"/folders/{f['id']}", json=body, headers=ALICE).status_code == 422
    assert _folders()[0]["name"] == "Term 3"


def test_duplicate_names_are_allowed():
    _folder("Same")
    _folder("Same")
    assert [f["name"] for f in _folders()] == ["Same", "Same"]


def test_documents_list_carries_folder_id_and_folders_count_papers():
    folder = _folder()
    filed = _paper(folder_id=folder["id"])
    loose = _paper()
    assert filed["folder_id"] == folder["id"] and loose["folder_id"] is None
    assert _doc_ids() == {filed["id"]: folder["id"], loose["id"]: None}
    assert _folders()[0]["papers"] == 1


def test_move_does_not_change_version_or_content():
    folder = _folder()
    rec = _paper()
    doc = make_doc(para("Go."), gen_block(), title="Paper")
    saved = client.put(
        f"/documents/{rec['id']}", json={"document": doc, "base_version": 1}, headers=ALICE
    ).json()
    assert saved["version"] == 2
    before = client.get(f"/documents/{rec['id']}", headers=ALICE).json()

    moved = _move(rec["id"], folder["id"])
    assert moved.status_code == 200
    assert moved.json()["folder_id"] == folder["id"] and moved.json()["version"] == 2
    after = client.get(f"/documents/{rec['id']}", headers=ALICE).json()
    assert after["document"] == before["document"]
    assert after["version"] == 2 and after["updated_at"] == before["updated_at"]
    assert after["folder_id"] == folder["id"]
    # an editor holding version 2 still saves cleanly, and the paper stays filed
    resaved = client.put(
        f"/documents/{rec['id']}", json={"document": doc, "base_version": 2}, headers=ALICE
    )
    assert resaved.status_code == 200 and resaved.json()["folder_id"] == folder["id"]

    unfiled = _move(rec["id"], None)
    assert unfiled.status_code == 200 and unfiled.json()["folder_id"] is None
    assert _folders()[0]["papers"] == 0


def test_move_needs_the_folder_id_field_and_known_ids():
    rec = _paper()
    assert client.patch(f"/documents/{rec['id']}", json={}, headers=ALICE).status_code == 422
    assert _move(rec["id"], "nope").status_code == 404
    assert _move("nope", None).status_code == 404


def test_deleting_a_folder_unfiles_its_papers():
    folder = _folder()
    rec = _paper(folder_id=folder["id"])
    assert client.delete(f"/folders/{folder['id']}", headers=ALICE).status_code == 204
    kept = client.get(f"/documents/{rec['id']}", headers=ALICE)
    assert kept.status_code == 200
    assert kept.json()["folder_id"] is None and kept.json()["version"] == 1


def test_owner_isolation():
    alices = _folder("Alice's")
    alices_paper = _paper(folder_id=alices["id"])
    bobs_paper = _paper(BOB)
    assert _folders(BOB) == []
    fid = alices["id"]
    assert client.patch(f"/folders/{fid}", json={"name": "x"}, headers=BOB).status_code == 404
    assert client.delete(f"/folders/{fid}", headers=BOB).status_code == 404
    assert _move(bobs_paper["id"], fid, BOB).status_code == 404
    assert _move(alices_paper["id"], None, BOB).status_code == 404
    assert client.post("/documents", json={"folder_id": fid}, headers=BOB).status_code == 404
    resp = client.post(
        "/documents/generate", json={"template": "p2", "seed": 5, "folder_id": fid}, headers=BOB
    )
    assert resp.status_code == 404
    assert _doc_ids(BOB) == {bobs_paper["id"]: None}
    (still,) = _folders()
    assert still["name"] == "Alice's" and still["papers"] == 1
    assert _doc_ids() == {alices_paper["id"]: fid}


def test_create_from_a_template_and_generate_into_a_folder():
    folder = _folder("Exam set")
    templ = _paper(template="p1_booklet_a", folder_id=folder["id"])
    assert templ["folder_id"] == folder["id"]
    gen = client.post(
        "/documents/generate",
        json={"template": "p2", "level": "P6", "seed": 5, "folder_id": folder["id"]},
        headers=ALICE,
    )
    assert gen.status_code == 201
    assert gen.json()["folder_id"] == folder["id"] and gen.json()["report"]
    assert _folders()[0]["papers"] == 2
    unknown = client.post(
        "/documents/generate",
        json={"template": "p2", "seed": 5, "folder_id": "nope"},
        headers=ALICE,
    )
    assert unknown.status_code == 404
    assert len(_doc_ids()) == 2


@pytest.mark.skipif(
    os.environ.get("EXAM_TEST_BACKEND") == "postgres",
    reason="the SQLite file upgrade; Postgres adds the column in its own boot DDL",
)
def test_an_older_documents_file_gains_the_column_and_its_papers_are_unfiled(tmp_path, monkeypatch):
    path = tmp_path / "old-docs.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE documents (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, "
            "title TEXT NOT NULL, document TEXT NOT NULL, total_marks INTEGER NOT NULL, "
            "version INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
            ("old", "alice", "Old", json.dumps(empty_document("Old")), 0, 4, "t0", "t0"),
        )
    monkeypatch.setenv("EXAM_DOCS_PATH", str(path))
    (old,) = client.get("/documents", headers=ALICE).json()["documents"]
    assert old["id"] == "old" and old["folder_id"] is None and old["version"] == 4
    folder = _folder()
    assert _move("old", folder["id"]).json()["folder_id"] == folder["id"]
    assert _folders()[0]["papers"] == 1


def _zip(resp) -> zipfile.ZipFile:
    assert resp.status_code == 200
    return zipfile.ZipFile(io.BytesIO(resp.content))


def test_account_export_includes_folders_and_delete_erases_them():
    folder = _folder("Prelims")
    rec = _paper(folder_id=folder["id"])
    _folder("Bob's", BOB)
    zf = _zip(client.get("/account/export", headers=ALICE))
    (exported,) = json.loads(zf.read("folders.json"))
    assert exported["id"] == folder["id"] and exported["name"] == "Prelims"
    assert exported["papers"] == 1
    assert json.loads(zf.read("account.json"))["counts"]["folders"] == 1
    assert json.loads(zf.read(f"documents/{rec['id']}.json"))["folder_id"] == folder["id"]

    resp = client.request("DELETE", "/account", json={"confirm": "DELETE"}, headers=ALICE)
    assert resp.status_code == 204
    assert _folders() == []
    erased = _zip(client.get("/account/export", headers=ALICE))
    assert json.loads(erased.read("folders.json")) == []
    assert [f["name"] for f in _folders(BOB)] == ["Bob's"]


def test_folder_names_collapse_whitespace_and_drop_control_characters():
    resp = client.post("/folders", json={"name": "  2026\n Prelims\t set\x07 "}, headers=ALICE)
    assert resp.status_code == 201 and resp.json()["name"] == "2026 Prelims set"
