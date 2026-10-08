"""W1b — /documents API: auth seam, tenant isolation, validation, conflict, export."""

from __future__ import annotations

import pytest
from app.main import app
from documents import gen_block, heading, make_doc, para, question_block
from exam_engine import generate
from fastapi.testclient import TestClient
from test_export_api import requires_chromium

client = TestClient(app)
ALICE = {"X-Dev-Owner": "alice"}
BOB = {"X-Dev-Owner": "bob"}


@pytest.fixture(autouse=True)
def _dev_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")
    monkeypatch.setenv("EXAM_DOCS_PATH", str(tmp_path / "docs.sqlite3"))


def _create(headers=ALICE, title="Paper") -> dict:
    resp = client.post("/documents", json={"title": title}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _save(rec: dict, document: dict, headers=ALICE, version: int | None = None):
    return client.put(
        f"/documents/{rec['id']}",
        json={"document": document, "base_version": version or rec["version"]},
        headers=headers,
    )


def test_auth_fails_closed_without_dev_flag(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert client.get("/documents", headers=ALICE).status_code == 401
    assert client.post("/documents", json={}, headers=ALICE).status_code == 401


def test_invalid_owner_header_rejected():
    assert client.get("/documents", headers={"X-Dev-Owner": "bad owner!"}).status_code == 400


def test_default_owner_is_dev():
    assert client.post("/documents", json={}).status_code == 201
    assert len(client.get("/documents").json()["documents"]) == 1


def test_crud_happy_path():
    rec = _create(title="Ratio review")
    assert rec["version"] == 1 and rec["title"] == "Ratio review"
    assert rec["document"]["content"]["content"] == []

    doc = make_doc(heading("Section A"), para("Go."), gen_block(), title="Ratio review 2")
    saved = _save(rec, doc)
    assert saved.status_code == 200
    body = saved.json()
    assert body["version"] == 2 and body["title"] == "Ratio review 2" and body["total_marks"] > 0

    got = client.get(f"/documents/{rec['id']}", headers=ALICE).json()
    assert got["document"] == doc

    listing = client.get("/documents", headers=ALICE).json()["documents"]
    assert [d["id"] for d in listing] == [rec["id"]] and "document" not in listing[0]
    assert listing[0]["total_marks"] == body["total_marks"]

    assert client.delete(f"/documents/{rec['id']}", headers=ALICE).status_code == 204
    assert client.get(f"/documents/{rec['id']}", headers=ALICE).status_code == 404


def test_untitled_default():
    assert client.post("/documents", json={}, headers=ALICE).json()["title"] == "Untitled paper"


def test_other_owners_documents_are_404_everywhere():
    rec = _create()
    url = f"/documents/{rec['id']}"
    assert client.get(url, headers=BOB).status_code == 404
    assert _save(rec, make_doc(title="pwned"), headers=BOB).status_code == 404
    assert client.delete(url, headers=BOB).status_code == 404
    assert client.get(f"{url}/preview/full", headers=BOB).status_code == 404
    assert client.post(f"{url}/export/student", headers=BOB).status_code == 404
    assert client.get("/documents", headers=BOB).json()["documents"] == []
    assert client.get(url, headers=ALICE).json()["title"] == "Paper"


def test_stale_save_is_409_with_current_version():
    rec = _create()
    assert _save(rec, make_doc(title="one")).status_code == 200
    resp = _save(rec, make_doc(title="two"), version=1)
    assert resp.status_code == 409
    assert resp.json()["detail"]["current_version"] == 2


def test_invalid_content_is_422_with_paths():
    rec = _create()
    resp = _save(rec, make_doc({"type": "image"}))
    assert resp.status_code == 422 and isinstance(resp.json()["detail"], list)

    tampered = generate("ratio_medium", 3)
    tampered["question"]["parts"][0]["answer"]["value"] += 1
    resp = _save(rec, make_doc(question_block(tampered)))
    assert resp.status_code == 422
    assert any("does not match" in e for e in resp.json()["detail"])
    assert client.get(f"/documents/{rec['id']}", headers=ALICE).json()["version"] == 1


def test_oversize_save_rejected():
    rec = _create()
    big = make_doc(*[para("x" * 20000) for _ in range(100)])
    assert _save(rec, big).status_code in (413, 422)


def test_preview_modes_and_unknown_mode():
    rec = _create()
    doc = make_doc(para("Intro"), gen_block("ratio_easy", 4))
    _save(rec, doc)
    student = client.get(f"/documents/{rec['id']}/preview/student", headers=ALICE)
    assert student.status_code == 200 and student.headers["content-type"].startswith("text/html")
    assert "Answer:" not in student.text and "Intro" in student.text
    key = client.get(f"/documents/{rec['id']}/preview/key", headers=ALICE)
    assert "Answer:" in key.text
    full = client.get(f"/documents/{rec['id']}/preview/full", headers=ALICE)
    assert "key-section" in full.text
    assert client.get(f"/documents/{rec['id']}/preview/teacher", headers=ALICE).status_code == 422


def test_key_export_needs_questions():
    rec = _create()
    _save(rec, make_doc(para("only text")))
    assert client.get(f"/documents/{rec['id']}/preview/key", headers=ALICE).status_code == 422
    assert client.get(f"/documents/{rec['id']}/preview/student", headers=ALICE).status_code == 200


@requires_chromium
@pytest.mark.parametrize(
    ("mode", "suffix"), [("student", "student"), ("key", "answer-key"), ("full", "full")]
)
def test_export_pdf(mode, suffix):
    rec = _create(title="My Paper!")
    _save(
        rec,
        make_doc(
            heading("A"),
            gen_block("ratio_medium", 2),
            gen_block("speed_easy", 2),
            title="My Paper!",
        ),
    )
    resp = client.post(f"/documents/{rec['id']}/export/{mode}", headers=ALICE)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    assert f'filename="my-paper-{suffix}.pdf"' in resp.headers["content-disposition"]


def test_export_concurrency_slot_is_bounded(monkeypatch):
    import threading

    from app import quota

    monkeypatch.setattr(quota, "_SEMAPHORE", threading.BoundedSemaphore(1))
    monkeypatch.setattr(quota, "_ACQUIRE_TIMEOUT_S", 0.05)
    with quota.export_slot():
        with pytest.raises(Exception) as err, quota.export_slot():
            pass
        assert getattr(err.value, "status_code", None) == 503
    with quota.export_slot():  # released afterwards
        pass
