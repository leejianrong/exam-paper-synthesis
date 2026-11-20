"""P8d — POST /documents/{id}/swap and POST /documents/{id}/regenerate."""

from __future__ import annotations

import pytest
from app.bankstore import open_owner_bank
from app.main import app
from app.ops import strip_document_hints
from exam_engine.document import paper_outline, validate_document
from fastapi.testclient import TestClient
from test_paper_swap_bank import bank_obj

client = TestClient(app)
ALICE = {"X-Dev-Owner": "alice"}
BOB = {"X-Dev-Owner": "bob"}


@pytest.fixture(autouse=True)
def _dev_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")
    monkeypatch.setenv("EXAM_DOCS_PATH", str(tmp_path / "docs.sqlite3"))


def _paper(template="p2", seed=5) -> dict:
    resp = client.post(
        "/documents/generate",
        json={"template": template, "level": "P6", "seed": seed},
        headers=ALICE,
    )
    assert resp.status_code == 201
    return resp.json()


def _questions(rec):
    return [n for n in rec["document"]["content"]["content"] if n["type"].endswith("Question")]


def _swap(rec, block_id, mode, headers=ALICE, **extra):
    return client.post(
        f"/documents/{rec['id']}/swap",
        json={"block_id": block_id, "mode": mode, "base_version": rec["version"], **extra},
        headers=headers,
    )


def test_swap_saves_a_new_version_with_hints_and_a_report():
    rec = _paper()
    q = _questions(rec)[0]
    resp = _swap(rec, q["attrs"]["block_id"], "like")
    assert resp.status_code == 200
    out = resp.json()
    assert out["version"] == rec["version"] + 1
    assert out["report"]["block_id"] == q["attrs"]["block_id"]
    assert out["report"]["marks"] == q["attrs"]["slot"]["marks"]
    new = next(n for n in _questions(out) if n["attrs"]["block_id"] == q["attrs"]["block_id"])
    assert new["attrs"]["question"]["id"] != q["attrs"]["question"]["id"]
    assert new["attrs"]["question"]["provenance"]["created_at"]  # stamped at the boundary
    assert "available_ops" in new["attrs"]["question"]  # hints, as for GET
    stored = client.get(f"/documents/{rec['id']}", headers=ALICE).json()
    assert stored["version"] == out["version"]
    assert validate_document(strip_document_hints(stored["document"])) == []
    assert [s["marks"] for s in paper_outline(stored["document"])] == [10, 45]


def test_write_my_own_leaves_an_empty_placeholder_with_the_slots_marks():
    rec = _paper()
    q = _questions(rec)[-1]
    out = _swap(rec, q["attrs"]["block_id"], "own").json()
    new = next(n for n in _questions(out) if n["attrs"]["block_id"] == q["attrs"]["block_id"])
    assert new["type"] == "freeformQuestion"
    assert new["attrs"]["marks"] == q["attrs"]["slot"]["marks"]
    assert new["attrs"]["slot"]["placeholder"] is True


def test_a_stale_version_is_a_conflict_and_changes_nothing():
    rec = _paper()
    q = _questions(rec)[0]
    stale = {**rec, "version": rec["version"] - 1}
    resp = _swap(stale, q["attrs"]["block_id"], "like")
    assert resp.status_code == 409
    assert resp.json()["detail"]["current_version"] == rec["version"]
    regen = client.post(
        f"/documents/{rec['id']}/regenerate", json={"base_version": 99}, headers=ALICE
    )
    assert regen.status_code == 409
    assert client.get(f"/documents/{rec['id']}", headers=ALICE).json()["version"] == rec["version"]


def test_swaps_are_owner_scoped_and_need_an_identity(monkeypatch):
    rec = _paper()
    q = _questions(rec)[0]
    assert _swap(rec, q["attrs"]["block_id"], "like", headers=BOB).status_code == 404
    regen = client.post(
        f"/documents/{rec['id']}/regenerate", json={"base_version": rec["version"]}, headers=BOB
    )
    assert regen.status_code == 404
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert _swap(rec, q["attrs"]["block_id"], "like", headers={}).status_code == 401


def test_bad_requests_are_refused_with_a_reason():
    rec = _paper("p1_booklet_b", 1)
    qs = _questions(rec)
    assert _swap(rec, "nope_1234", "like").status_code == 404
    assert _swap(rec, qs[0]["attrs"]["block_id"], "sideways").status_code == 422
    assert _swap(rec, qs[0]["attrs"]["block_id"], "like", level="P4").status_code == 422
    rec = _swap(rec, qs[-1]["attrs"]["block_id"], "own").json()  # a placeholder to refuse
    placeholder = next(n for n in _questions(rec) if n["type"] == "freeformQuestion")
    resp = _swap(rec, placeholder["attrs"]["block_id"], "own")
    assert resp.status_code == 422 and "already" in resp.json()["detail"]
    # a locked question can't be swapped
    doc = strip_document_hints(rec["document"])
    blocks = doc["content"]["content"]
    target = next(n for n in blocks if n["type"] == "templatedQuestion")
    target["attrs"]["locked"] = True
    saved = client.put(
        f"/documents/{rec['id']}",
        json={"document": doc, "base_version": rec["version"]},
        headers=ALICE,
    ).json()
    resp = _swap(saved, target["attrs"]["block_id"], "like")
    assert resp.status_code == 422 and "locked" in resp.json()["detail"]


def test_regenerate_keeps_locked_questions():
    rec = _paper()
    doc = strip_document_hints(rec["document"])
    blocks = doc["content"]["content"]
    locked = [n for n in blocks if n["type"] == "templatedQuestion"][:3]
    for n in locked:
        n["attrs"]["locked"] = True
    saved = client.put(
        f"/documents/{rec['id']}",
        json={"document": doc, "base_version": rec["version"]},
        headers=ALICE,
    ).json()
    resp = client.post(
        f"/documents/{rec['id']}/regenerate",
        json={"base_version": saved["version"], "seed": 3},
        headers=ALICE,
    )
    assert resp.status_code == 200
    out = resp.json()
    questions = sum(n["type"] == "templatedQuestion" for n in blocks)  # 17-18 in a P6 Paper 2
    assert out["report"]["kept"] == 3 and out["report"]["replaced"] == questions - 3
    after = {
        n["attrs"]["block_id"]: n
        for n in strip_document_hints(out["document"])["content"]["content"]
        if "attrs" in n and "block_id" in (n["attrs"] or {})
    }
    for n in locked:
        assert after[n["attrs"]["block_id"]] == n
    assert [s["marks"] for s in paper_outline(out["document"])] == [10, 45]


def test_only_a_missing_block_is_a_404(monkeypatch):
    from exam_engine import paper_swap

    rec = _paper()
    q = _questions(rec)[0]

    def boom(*a, **k):
        raise KeyError("an engine bug, not a missing block")

    monkeypatch.setattr(paper_swap, "swap_question", boom)
    with pytest.raises(KeyError):
        _swap(rec, q["attrs"]["block_id"], "like")


# --- EXA-33: swap from the owner's bank -------------------------------------------------


def _bank(monkeypatch, tmp_path, owner, *objs):
    monkeypatch.setenv("EXAM_BANK_PATH", str(tmp_path / "bank.sqlite3"))
    bank = open_owner_bank(owner)
    for obj in objs:
        bank.add(obj)
    bank.close()


def _short_2(rec):
    return next(
        n for n in _questions(rec) if n["attrs"].get("slot") == {"marks": 2, "kind": "short"}
    )


def _options(rec, block_id, headers=ALICE):
    return client.get(
        f"/documents/{rec['id']}/swap/bank", params={"block_id": block_id}, headers=headers
    )


def test_bank_options_are_the_owners_own_fitting_questions(monkeypatch, tmp_path):
    mine = bank_obj("standin_chart_line", "alice-2")
    too_big = bank_obj("standin_chart_bar", "alice-3")
    _bank(monkeypatch, tmp_path, "alice", mine, too_big)
    _bank(monkeypatch, tmp_path, "bob", bank_obj("standin_chart_pie", "bob-2"))
    rec = _paper()
    q = _short_2(rec)
    resp = _options(rec, q["attrs"]["block_id"])
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [i["id"] for i in items] == [mine["id"]]
    assert items[0]["reviewed"] is False and items[0]["topic"] == "Statistics"
    assert _options(rec, q["attrs"]["block_id"], headers=BOB).status_code == 404  # her paper
    assert _options(rec, "nope").status_code == 404


def test_swap_from_the_bank_saves_the_bank_snapshot(monkeypatch, tmp_path):
    obj = bank_obj("standin_chart_line", "alice-2")
    _bank(monkeypatch, tmp_path, "alice", obj)
    rec = _paper()
    q = _short_2(rec)
    resp = _swap(rec, q["attrs"]["block_id"], "bank", bank_id=obj["id"])
    assert resp.status_code == 200, resp.text
    out = resp.json()
    assert out["version"] == rec["version"] + 1
    assert out["report"]["bank_id"] == obj["id"] and out["report"]["mode"] == "bank"
    new = next(n for n in _questions(out) if n["attrs"]["block_id"] == q["attrs"]["block_id"])
    assert new["attrs"]["question"]["id"] == obj["id"]
    assert new["attrs"]["question"]["source_type"] == "sourced"
    stored = client.get(f"/documents/{rec['id']}", headers=ALICE).json()
    assert validate_document(strip_document_hints(stored["document"])) == []
    assert [s["marks"] for s in paper_outline(stored["document"])] == [10, 45]
    # now in the paper: not offered again, and a second copy is refused
    other = next(
        n
        for n in _questions(out)
        if n["attrs"].get("slot") == {"marks": 2, "kind": "short"}
        and n["attrs"]["block_id"] != q["attrs"]["block_id"]
    )
    assert _options(out, other["attrs"]["block_id"]).json()["items"] == []
    again = _swap(out, other["attrs"]["block_id"], "bank", bank_id=obj["id"])
    assert again.status_code == 422 and "already in this paper" in again.json()["detail"]


def test_bank_swap_never_reaches_another_owners_bank(monkeypatch, tmp_path):
    theirs = bank_obj("standin_chart_line", "bob-2")
    _bank(monkeypatch, tmp_path, "bob", theirs)
    rec = _paper()
    q = _short_2(rec)
    resp = _swap(rec, q["attrs"]["block_id"], "bank", bank_id=theirs["id"])
    assert resp.status_code == 404
    assert _swap(rec, q["attrs"]["block_id"], "bank").status_code == 422  # no bank_id
    assert client.get(f"/documents/{rec['id']}", headers=ALICE).json()["version"] == rec["version"]


def test_bank_swap_refuses_a_misfit_a_locked_question_and_a_stale_version(monkeypatch, tmp_path):
    fits, big = bank_obj("standin_chart_line", "a"), bank_obj("standin_chart_bar", "b")
    _bank(monkeypatch, tmp_path, "alice", fits, big)
    rec = _paper()
    q = _short_2(rec)
    bid = q["attrs"]["block_id"]
    misfit = _swap(rec, bid, "bank", bank_id=big["id"])
    assert misfit.status_code == 422 and "2-mark" in misfit.json()["detail"]
    stale = _swap({**rec, "version": rec["version"] - 1}, bid, "bank", bank_id=fits["id"])
    assert stale.status_code == 409
    q["attrs"]["locked"] = True
    saved = client.put(
        f"/documents/{rec['id']}",
        json={"document": strip_document_hints(rec["document"]), "base_version": rec["version"]},
        headers=ALICE,
    ).json()
    locked = _swap(saved, bid, "bank", bank_id=fits["id"])
    assert locked.status_code == 422 and "locked" in locked.json()["detail"]
    assert _options(saved, bid).status_code == 422
