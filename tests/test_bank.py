"""A1/A2/A10 — engine-level Bank roundtrip/search/review tests (KAN-663 E1)."""

from __future__ import annotations

import pytest
from exam_engine import generate
from exam_engine.bank import Bank
from exam_engine.canonical import CanonicalValidationError
from exam_engine.errors import BankDuplicateId, BankObjectNotFound


@pytest.fixture
def bank(tmp_path):
    with Bank(tmp_path / "bank.sqlite3") as b:
        yield b


def test_add_get_roundtrip(bank):
    obj = generate("ratio_medium", 1)
    assert obj["provenance"]["created_at"] is None

    stored = bank.add(obj)
    assert stored["provenance"]["created_at"] is not None

    fetched = bank.get(obj["id"])
    assert fetched == stored


def test_add_rejects_invalid_object(bank):
    obj = generate("ratio_medium", 1)
    del obj["schema_version"]  # required field -> invalid
    with pytest.raises(CanonicalValidationError):
        bank.add(obj)
    with pytest.raises(BankObjectNotFound):
        bank.get("ratio_medium:1")


def test_add_duplicate_id(bank):
    obj = generate("ratio_medium", 1)
    bank.add(obj)
    with pytest.raises(BankDuplicateId):
        bank.add(obj)

    stored = bank.add(obj, overwrite=True)
    assert stored["id"] == obj["id"]


def test_search_filters(bank):
    ratio = generate("ratio_medium", 1)
    fractions = generate("fractions_easy", 2)
    bank.add(ratio)
    bank.add(fractions)
    bank.mark_reviewed(ratio["id"])

    assert [o["id"] for o in bank.search(topic=ratio["syllabus"]["topic"])] == [ratio["id"]]
    assert [o["id"] for o in bank.search(difficulty="easy")] == [fractions["id"]]
    assert [o["id"] for o in bank.search(reviewed=False)] == [fractions["id"]]
    assert [o["id"] for o in bank.search(reviewed=True)] == [ratio["id"]]

    everything = {o["id"] for o in bank.search()}
    assert everything == {ratio["id"], fractions["id"]}


def test_mark_reviewed(bank):
    obj = generate("ratio_medium", 1)
    bank.add(obj)

    reviewed = bank.mark_reviewed(obj["id"])
    assert reviewed["validation"]["checks"]["human_reviewed"] is True
    assert reviewed["provenance"]["version"] == 2
    assert reviewed["id"] == obj["id"]
    assert reviewed["provenance"]["created_at"] == bank.get(obj["id"])["provenance"]["created_at"]

    assert [o["id"] for o in bank.search(reviewed=True)] == [obj["id"]]


def test_update_unknown_id_raises(bank):
    obj = generate("ratio_medium", 1)
    with pytest.raises(BankObjectNotFound):
        bank.update(obj)
    with pytest.raises(BankObjectNotFound):
        bank.mark_reviewed("does-not-exist")


def test_reviewed_column_never_drifts(bank):
    obj = generate("ratio_medium", 1)
    bank.add(obj)

    fetched = bank.get(obj["id"])
    fetched["validation"]["checks"]["human_reviewed"] = True  # mutate the returned dict only

    assert bank.search(reviewed=True) == []
    assert bank.get(obj["id"])["validation"]["checks"].get("human_reviewed") is not True


# --- W1d: owner scoping --------------------------------------------------------


def test_banks_are_isolated_per_owner(tmp_path):
    path = tmp_path / "bank.sqlite3"
    obj = generate("ratio_medium", 1)
    with Bank(path, "alice") as a, Bank(path, "bob") as b:
        a.add(obj)
        assert [o["id"] for o in a.search()] == [obj["id"]]
        assert b.search() == []
        with pytest.raises(BankObjectNotFound):
            b.get(obj["id"])
        with pytest.raises(BankObjectNotFound):
            b.mark_reviewed(obj["id"])
        # The same id is a different row for another owner (no cross-tenant collision).
        b.add(obj)
        a.mark_reviewed(obj["id"])
        assert [o["validation"]["checks"].get("human_reviewed") for o in a.search()] == [True]
        assert not b.get(obj["id"])["validation"]["checks"].get("human_reviewed")
        assert len(b.search(reviewed=True)) == 0


def test_default_owner_is_local_and_cli_compatible(tmp_path):
    path = tmp_path / "bank.sqlite3"
    with Bank(path) as cli_view:
        assert cli_view.owner_id == "local"
        cli_view.add(generate("ratio_medium", 2))
    with Bank(path, "local") as same:
        assert len(same.search()) == 1
    with Bank(path, "someone-else") as other:
        assert other.search() == []


def test_pre_owner_database_is_migrated_to_the_local_owner(tmp_path):
    import sqlite3

    path = tmp_path / "old.sqlite3"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE objects (
            id TEXT PRIMARY KEY, schema_version TEXT NOT NULL, source_type TEXT NOT NULL,
            topic TEXT, level TEXT, difficulty TEXT, created_by TEXT NOT NULL,
            reviewed INTEGER NOT NULL DEFAULT 0, imported_at TEXT NOT NULL, json TEXT NOT NULL
        );
        CREATE INDEX idx_objects_topic ON objects(topic);
        """
    )
    from exam_engine import canonical

    obj = generate("ratio_medium", 3)
    conn.execute(
        "INSERT INTO objects VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            obj["id"],
            obj["schema_version"],
            obj["source_type"],
            "Ratio",
            "P5",
            "medium",
            "engine",
            0,
            "2026-01-01T00:00:00+00:00",
            canonical.to_json(obj),
        ),
    )
    conn.commit()
    conn.close()

    with Bank(path) as local:
        assert [o["id"] for o in local.search()] == [obj["id"]]
        assert local.search(topic="Ratio")  # indexed columns survived
    with Bank(path, "alice") as alice:
        assert alice.search() == []
        alice.add(obj)  # same id under another owner works after migration
    with Bank(path) as again:  # idempotent: opening twice keeps the data
        assert len(again.search()) == 1
