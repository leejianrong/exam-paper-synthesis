"""W3b — the bank surface the API uses (search / add / get), over every backend.

The engine's SQLite ``Bank`` (also the CLI's) and the Postgres ``PgBank`` must agree, including
owner isolation and the duplicate / overwrite rules.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from exam_engine.bank import Bank
from exam_engine.errors import BankDuplicateId, BankObjectNotFound

SOURCED = Path(__file__).parent / "fixtures" / "sourced"


def fixture(name: str) -> dict:
    return json.loads((SOURCED / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(params=["sqlite", "postgres"])
def open_bank(request, tmp_path):
    if request.param == "sqlite":
        return lambda owner: Bank(tmp_path / "bank.sqlite3", owner)
    from app.pgstores import PgBank

    db = request.getfixturevalue("pg_db")
    return lambda owner: PgBank(db, owner)


def test_add_get_roundtrip_and_search_order(open_bank):
    bank = open_bank("alice")
    mcq, table = fixture("psle_2023_mcq"), fixture("psle_2023_table")
    stored = bank.add(mcq)
    assert stored["id"] == mcq["id"] and stored["provenance"]["created_at"]
    bank.add(table)
    assert bank.get(mcq["id"])["id"] == mcq["id"]
    assert [o["id"] for o in bank.search()] == [mcq["id"], table["id"]]
    with pytest.raises(BankObjectNotFound):
        bank.get("sourced:nope")


def test_duplicates_need_overwrite_and_keep_their_place(open_bank):
    bank = open_bank("alice")
    mcq, table = fixture("psle_2023_mcq"), fixture("psle_2023_table")
    bank.add(mcq)
    bank.add(table)
    with pytest.raises(BankDuplicateId):
        bank.add(mcq)
    edited = {**mcq, "question": {**mcq["question"], "stem": "Edited."}}
    bank.add(edited, overwrite=True)
    assert bank.get(mcq["id"])["question"]["stem"] == "Edited."
    assert [o["id"] for o in bank.search()] == [mcq["id"], table["id"]]  # order unchanged


def test_invalid_objects_are_refused(open_bank):
    from exam_engine.canonical import CanonicalValidationError

    broken = fixture("psle_2023_mcq")
    del broken["question"]["total_marks"]
    with pytest.raises(CanonicalValidationError):
        open_bank("alice").add(broken)


def test_owners_never_see_each_other(open_bank):
    mcq = fixture("psle_2023_mcq")
    open_bank("alice").add(mcq)
    bob = open_bank("bob")
    assert bob.search() == []
    with pytest.raises(BankObjectNotFound):
        bob.get(mcq["id"])
    bob.add(mcq)  # the same id under another owner is a different row
    assert len(open_bank("alice").search()) == 1 and len(bob.search()) == 1


def test_filters(open_bank):
    bank = open_bank("alice")
    mcq, table = fixture("psle_2023_mcq"), fixture("psle_2023_table")
    bank.add(mcq)
    bank.add(table)
    topic = mcq["syllabus"]["topic"]
    assert mcq["id"] in [o["id"] for o in bank.search(topic=topic)]
    assert bank.search(topic="no-such-topic") == []
    assert bank.search(source_type="generated") == []
    assert len(bank.search(source_type="sourced")) == 2
    assert bank.search(reviewed=True) == []
    assert len(bank.search(reviewed=False)) == 2
    reviewed = json.loads(json.dumps(mcq))
    reviewed.setdefault("validation", {}).setdefault("checks", {})["human_reviewed"] = True
    bank.add(reviewed, overwrite=True)
    assert [o["id"] for o in bank.search(reviewed=True)] == [mcq["id"]]


def test_mark_reviewed_bumps_version_and_flags_the_row(open_bank):
    bank = open_bank("alice")
    mcq = fixture("psle_2023_mcq")
    before = bank.add(mcq)
    after = bank.mark_reviewed(mcq["id"])
    assert after["validation"]["checks"]["human_reviewed"] is True
    assert after["provenance"]["version"] == before["provenance"]["version"] + 1
    assert [o["id"] for o in bank.search(reviewed=True)] == [mcq["id"]]


def test_erase_removes_only_this_owners_questions(open_bank):
    mcq, table = fixture("psle_2023_mcq"), fixture("psle_2023_table")
    alice, bob = open_bank("alice"), open_bank("bob")
    alice.add(mcq)
    alice.add(table)
    bob.add(mcq)
    assert alice.erase() == 2
    assert alice.search() == []
    assert [o["id"] for o in bob.search()] == [mcq["id"]]
    assert alice.erase() == 0
