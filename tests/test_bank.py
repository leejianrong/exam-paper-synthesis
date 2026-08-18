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
