"""W1b — document-store contract (ADR-0022). Parametrised over implementations so W3's
Postgres store must pass this identical suite, including tenant isolation."""

from __future__ import annotations

import sqlite3

import pytest
from app.docstore import (
    DocumentNotFound,
    FolderNotFound,
    InvalidFolderName,
    SqliteDocumentStore,
    VersionConflict,
)
from documents import gen_block, make_doc, para
from exam_engine import paper
from exam_engine.document import empty_document, total_marks


@pytest.fixture(params=["sqlite", "postgres"])
def store(request, tmp_path):
    if request.param == "sqlite":
        return SqliteDocumentStore(tmp_path / "docs.sqlite3")
    if request.param == "postgres":
        from app.pgstores import PgDocumentStore

        return PgDocumentStore(request.getfixturevalue("pg_db"))
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


def test_erase_owner_removes_only_that_owners_documents(store):
    store.create("alice", empty_document("A1"), 0)
    store.create("alice", empty_document("A2"), 0)
    keep = store.create("bob", empty_document("B"), 0)
    assert store.erase_owner("alice") == 2
    assert store.list("alice") == []
    assert [d["id"] for d in store.list("bob")] == [keep["id"]]
    assert store.erase_owner("alice") == 0


# --- O2 folders --------------------------------------------------------------------------


def test_folder_crud_with_paper_counts(store):
    a = store.create_folder("alice", "  Term 3 prelims  ")
    assert a["name"] == "Term 3 prelims" and a["papers"] == 0
    assert a["created_at"] and a["updated_at"]
    b = store.create_folder("alice", "Drafts")
    store.create_folder("alice", "drafts")  # duplicates (any case) are allowed
    store.create("alice", empty_document("p1"), 0, a["id"])
    store.create("alice", empty_document("p2"), 0, a["id"])
    store.create("alice", empty_document("loose"), 0)
    listed = store.list_folders("alice")
    assert [f["name"] for f in listed] == ["Drafts", "drafts", "Term 3 prelims"]
    assert {f["id"]: f["papers"] for f in listed}[a["id"]] == 2
    assert {f["id"]: f["papers"] for f in listed}[b["id"]] == 0
    renamed = store.rename_folder("alice", b["id"], "Practice")
    assert renamed["name"] == "Practice" and renamed["id"] == b["id"]
    assert renamed["created_at"] == b["created_at"]


@pytest.mark.parametrize("name", ["", "   ", "x" * 81])
def test_folder_names_are_one_to_eighty_characters(store, name):
    with pytest.raises(InvalidFolderName):
        store.create_folder("alice", name)
    folder = store.create_folder("alice", "x" * 80)
    with pytest.raises(InvalidFolderName):
        store.rename_folder("alice", folder["id"], name)
    assert store.list_folders("alice")[0]["name"] == "x" * 80


def test_documents_carry_folder_id_and_existing_ones_are_unfiled(store):
    folder = store.create_folder("alice", "F")
    loose = store.create("alice", empty_document("loose"), 0)
    filed = store.create("alice", empty_document("filed"), 0, folder["id"])
    assert loose["folder_id"] is None and filed["folder_id"] == folder["id"]
    assert store.get("alice", filed["id"])["folder_id"] == folder["id"]
    by_id = {d["id"]: d["folder_id"] for d in store.list("alice")}
    assert by_id == {loose["id"]: None, filed["id"]: folder["id"]}


def test_records_carry_the_paper_part_from_the_cover(store):
    # O3: derived from the stored document, so the list (no content) still knows the part.
    starter = paper.template_document("p1_booklet_b")
    starter["title"] = "Renamed"
    rec = store.create("alice", starter, 0)
    blank = store.create("alice", empty_document("Paper 2 draft"), 0)
    none = store.create("alice", empty_document("Untitled"), 0)
    assert rec["paper_part"] == "booklet_b"
    parts = {d["id"]: d["paper_part"] for d in store.list("alice")}
    assert parts == {rec["id"]: "booklet_b", blank["id"]: "paper_2", none["id"]: None}
    folder = store.create_folder("alice", "F")
    assert store.move("alice", rec["id"], folder["id"])["paper_part"] == "booklet_b"


def test_move_files_and_unfiles_without_touching_content_or_version(store):
    folder = store.create_folder("alice", "F")
    doc = make_doc(para("hi"), gen_block(), title="Paper")
    rec = store.create("alice", doc, total_marks(doc))
    moved = store.move("alice", rec["id"], folder["id"])
    assert moved["folder_id"] == folder["id"] and "document" not in moved
    got = store.get("alice", rec["id"])
    assert got["version"] == 1 and got["document"] == doc
    assert got["updated_at"] == rec["updated_at"]
    assert store.list_folders("alice")[0]["papers"] == 1
    assert store.move("alice", rec["id"], None)["folder_id"] is None
    assert store.list_folders("alice")[0]["papers"] == 0
    # a save after a move keeps the folder
    store.move("alice", rec["id"], folder["id"])
    assert store.save("alice", rec["id"], doc, 1, 1)["folder_id"] == folder["id"]


def test_delete_folder_unfiles_its_papers_and_never_deletes_them(store):
    folder = store.create_folder("alice", "F")
    other = store.create_folder("alice", "G")
    a = store.create("alice", empty_document("a"), 0, folder["id"])
    b = store.create("alice", empty_document("b"), 0, other["id"])
    store.delete_folder("alice", folder["id"])
    assert [f["id"] for f in store.list_folders("alice")] == [other["id"]]
    assert store.get("alice", a["id"])["folder_id"] is None
    assert store.get("alice", a["id"])["version"] == 1
    assert store.get("alice", b["id"])["folder_id"] == other["id"]
    with pytest.raises(FolderNotFound):
        store.delete_folder("alice", folder["id"])


def test_folders_are_owner_scoped(store):
    mine = store.create_folder("alice", "Alice's")
    bobs_doc = store.create("bob", empty_document("bob"), 0)
    assert store.list_folders("bob") == []
    with pytest.raises(FolderNotFound):
        store.rename_folder("bob", mine["id"], "pwned")
    with pytest.raises(FolderNotFound):
        store.delete_folder("bob", mine["id"])
    with pytest.raises(FolderNotFound):  # bob can't file his paper in alice's folder
        store.move("bob", bobs_doc["id"], mine["id"])
    with pytest.raises(FolderNotFound):
        store.create("bob", empty_document("x"), 0, mine["id"])
    alices_doc = store.create("alice", empty_document("a"), 0)
    with pytest.raises(DocumentNotFound):  # nor move alice's paper
        store.move("bob", alices_doc["id"], None)
    assert [(d["id"], d["folder_id"]) for d in store.list("bob")] == [(bobs_doc["id"], None)]
    assert store.list_folders("alice")[0]["name"] == "Alice's"
    assert store.get("alice", alices_doc["id"])["folder_id"] is None


def test_unknown_folder_and_document_are_not_found(store):
    rec = store.create("alice", empty_document("a"), 0)
    with pytest.raises(FolderNotFound):
        store.move("alice", rec["id"], "nope")
    with pytest.raises(DocumentNotFound):
        store.move("alice", "nope", None)
    with pytest.raises(FolderNotFound):
        store.rename_folder("alice", "nope", "x")
    assert store.get("alice", rec["id"])["folder_id"] is None


def test_erase_owner_also_erases_folders(store):
    store.create_folder("alice", "A")
    store.create("alice", empty_document("a"), 0, store.create_folder("alice", "B")["id"])
    keep = store.create_folder("bob", "B")
    assert store.erase_owner("alice") == 1
    assert store.list_folders("alice") == []
    assert [f["id"] for f in store.list_folders("bob")] == [keep["id"]]


_OLD_SCHEMA = """
CREATE TABLE documents (
  id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, title TEXT NOT NULL, document TEXT NOT NULL,
  total_marks INTEGER NOT NULL, version INTEGER NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX documents_owner ON documents(owner_id, updated_at DESC);
"""


def test_folder_column_is_added_to_an_older_file_and_old_papers_are_unfiled(tmp_path):
    import json

    path = tmp_path / "old.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.executescript(_OLD_SCHEMA)
        conn.execute(
            "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
            ("old-1", "alice", "Old", json.dumps(empty_document("Old")), 0, 3, "t0", "t0"),
        )
    store = SqliteDocumentStore(path)
    SqliteDocumentStore(path)  # idempotent: a second open adds nothing
    with sqlite3.connect(path) as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(documents)")]
    assert cols.count("folder_id") == 1
    old = store.get("alice", "old-1")
    assert old["folder_id"] is None and old["version"] == 3 and old["title"] == "Old"
    folder = store.create_folder("alice", "Moved")
    assert store.move("alice", "old-1", folder["id"])["folder_id"] == folder["id"]
    new = store.create("alice", empty_document("New"), 0, folder["id"])
    assert store.list_folders("alice")[0]["papers"] == 2
    assert store.get("alice", new["id"])["title"] == "New"
