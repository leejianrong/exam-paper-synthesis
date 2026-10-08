"""W1b — document-store contract (ADR-0022). Parametrised over implementations so W3's
Postgres store must pass this identical suite, including tenant isolation."""

from __future__ import annotations

import pytest
from app.docstore import DocumentNotFound, SqliteDocumentStore, VersionConflict
from documents import gen_block, make_doc, para
from exam_engine.document import empty_document, total_marks


@pytest.fixture(params=["sqlite"])
def store(request, tmp_path):
    if request.param == "sqlite":
        return SqliteDocumentStore(tmp_path / "docs.sqlite3")
    raise AssertionError(request.param)  # pragma: no cover


def test_create_get_roundtrip(store):
    rec = store.create("alice", empty_document("My paper"), 0)
    assert rec["version"] == 1 and rec["title"] == "My paper"
    got = store.get("alice", rec["id"])
    assert got["document"] == empty_document("My paper")
    assert got["created_at"] and got["updated_at"]


def test_save_bumps_version_and_updates_fields(store):
    rec = store.create("alice", empty_document("A"), 0)
    doc = make_doc(para("hi"), gen_block(), title="B")
    saved = store.save("alice", rec["id"], doc, total_marks(doc), rec["version"])
    assert saved["version"] == 2 and saved["title"] == "B"
    assert saved["total_marks"] == total_marks(doc) > 0
    assert saved["document"] == doc


def test_stale_base_version_conflicts_and_changes_nothing(store):
    rec = store.create("alice", empty_document("A"), 0)
    store.save("alice", rec["id"], empty_document("B"), 0, 1)
    with pytest.raises(VersionConflict) as err:
        store.save("alice", rec["id"], empty_document("C"), 0, 1)
    assert err.value.current == 2
    assert store.get("alice", rec["id"])["title"] == "B"


def test_list_is_owner_scoped_newest_first_without_content(store):
    a1 = store.create("alice", empty_document("first"), 0)
    store.create("bob", empty_document("bobs"), 0)
    a2 = store.create("alice", empty_document("second"), 0)
    store.save("alice", a1["id"], empty_document("first!"), 0, 1)
    listed = store.list("alice")
    assert [d["id"] for d in listed] == [a1["id"], a2["id"]]
    assert all("document" not in d for d in listed)
    assert [d["title"] for d in store.list("bob")] == ["bobs"]
    assert store.list("carol") == []


def test_owner_isolation_get_save_delete(store):
    rec = store.create("alice", empty_document("secret"), 0)
    with pytest.raises(DocumentNotFound):
        store.get("bob", rec["id"])
    with pytest.raises(DocumentNotFound):
        store.save("bob", rec["id"], empty_document("pwned"), 0, 1)
    with pytest.raises(DocumentNotFound):
        store.delete("bob", rec["id"])
    mine = store.get("alice", rec["id"])
    assert mine["title"] == "secret" and mine["version"] == 1


def test_delete(store):
    rec = store.create("alice", empty_document("x"), 0)
    store.delete("alice", rec["id"])
    with pytest.raises(DocumentNotFound):
        store.get("alice", rec["id"])
    with pytest.raises(DocumentNotFound):
        store.delete("alice", rec["id"])


def test_missing_id_is_not_found(store):
    with pytest.raises(DocumentNotFound):
        store.get("alice", "nope")
    with pytest.raises(DocumentNotFound):
        store.save("alice", "nope", empty_document("x"), 0, 1)


def test_persists_across_instances(tmp_path):
    path = tmp_path / "docs.sqlite3"
    rec = SqliteDocumentStore(path).create("alice", empty_document("kept"), 0)
    assert SqliteDocumentStore(path).get("alice", rec["id"])["title"] == "kept"
