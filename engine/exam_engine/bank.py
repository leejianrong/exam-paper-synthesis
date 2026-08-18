"""A1/A2/A10 — the local question bank: a single SQLite file, schema-validated
rows (ADR-0017), with a review gate (ADR-0019).

One row per canonical object, stored as the exact JSON the engine's own load
gate (:mod:`canonical`) already validates on both write and read. A handful of
columns are denormalized out of that JSON purely for indexed search — never a
second source of truth.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from . import canonical
from .errors import BankDuplicateId, BankObjectNotFound

_DDL = """
CREATE TABLE IF NOT EXISTS objects (
    id             TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    source_type    TEXT NOT NULL,
    topic          TEXT,
    level          TEXT,
    difficulty     TEXT,
    created_by     TEXT NOT NULL,
    reviewed       INTEGER NOT NULL DEFAULT 0,
    imported_at    TEXT NOT NULL,
    json           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_objects_topic       ON objects(topic);
CREATE INDEX IF NOT EXISTS idx_objects_difficulty  ON objects(difficulty);
CREATE INDEX IF NOT EXISTS idx_objects_level       ON objects(level);
CREATE INDEX IF NOT EXISTS idx_objects_source_type ON objects(source_type);
CREATE INDEX IF NOT EXISTS idx_objects_reviewed    ON objects(reviewed);
"""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def default_path() -> Path:
    """Default bank location: ``~/.exam_engine/bank.sqlite3``.

    Override with ``EXAM_BANK_PATH`` — mirrors ``schema.schema_path()``'s
    ``EXAM_SCHEMA_PATH`` convention.
    """
    env = os.environ.get("EXAM_BANK_PATH")
    if env:
        return Path(env)
    return Path.home() / ".exam_engine" / "bank.sqlite3"


def open_bank(path: Path | None = None) -> Bank:
    """Open (creating if needed) the bank at ``path`` (default: :func:`default_path`)."""
    p = path if path is not None else default_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    return Bank(p)


def _reviewed_of(obj: dict) -> bool:
    return bool(obj.get("validation", {}).get("checks", {}).get("human_reviewed"))


class Bank:
    """A single SQLite-backed bank of canonical question objects."""

    def __init__(self, path: Path):
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DDL)
        self._conn.commit()

    def _row(self, id: str) -> sqlite3.Row | None:
        cur = self._conn.execute("SELECT * FROM objects WHERE id = ?", (id,))
        return cur.fetchone()

    def _upsert(self, obj: dict, imported_at: str) -> None:
        self._conn.execute(
            """
            INSERT INTO objects
                (id, schema_version, source_type, topic, level, difficulty,
                 created_by, reviewed, imported_at, json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                schema_version = excluded.schema_version,
                source_type    = excluded.source_type,
                topic          = excluded.topic,
                level          = excluded.level,
                difficulty     = excluded.difficulty,
                created_by     = excluded.created_by,
                reviewed       = excluded.reviewed,
                json           = excluded.json
            """,
            (
                obj["id"],
                obj["schema_version"],
                obj["source_type"],
                obj.get("syllabus", {}).get("topic"),
                obj.get("syllabus", {}).get("level"),
                obj.get("cognitive", {}).get("difficulty"),
                obj["provenance"]["created_by"],
                1 if _reviewed_of(obj) else 0,
                imported_at,
                canonical.to_json(obj),
            ),
        )
        self._conn.commit()

    def add(self, obj: dict, *, overwrite: bool = False) -> dict:
        """Insert a new object. Raises :class:`BankDuplicateId` unless ``overwrite=True``."""
        obj = canonical.load(dict(obj))
        existing = self._row(obj["id"])
        if existing is not None and not overwrite:
            raise BankDuplicateId(obj["id"])
        if not obj["provenance"].get("created_at"):
            obj["provenance"]["created_at"] = _now_iso()
            obj = canonical.load(obj)
        imported_at = existing["imported_at"] if existing is not None else _now_iso()
        self._upsert(obj, imported_at)
        return obj

    def get(self, id: str) -> dict:
        row = self._row(id)
        if row is None:
            raise BankObjectNotFound(id)
        return json.loads(row["json"])

    def update(self, obj: dict) -> dict:
        """Overwrite an existing row with a hand-corrected object.

        Bumps ``provenance.version``; preserves ``id`` and ``imported_at``.
        Re-validated against the canonical schema.
        """
        existing = self._row(obj["id"])
        if existing is None:
            raise BankObjectNotFound(obj["id"])
        old_version = json.loads(existing["json"])["provenance"].get("version", 1)
        obj = dict(obj)
        obj["provenance"] = dict(obj["provenance"])
        obj["provenance"]["version"] = old_version + 1
        obj = canonical.load(obj)
        self._upsert(obj, existing["imported_at"])
        return obj

    def mark_reviewed(self, id: str) -> dict:
        """Flip ``checks.human_reviewed`` and persist (ADR-0019's review action)."""
        obj = self.get(id)
        obj.setdefault("validation", {}).setdefault("checks", {})["human_reviewed"] = True
        return self.update(obj)

    def search(
        self,
        *,
        topic: str | None = None,
        difficulty: str | None = None,
        level: str | None = None,
        source_type: str | None = None,
        reviewed: bool | None = None,
    ) -> list[dict]:
        """Search over the indexed columns; all filters default to "no filter".

        ``search()`` with no arguments IS ``list`` — one query layer for both.
        """
        clauses = []
        params: list[object] = []
        if topic is not None:
            clauses.append("topic = ?")
            params.append(topic)
        if difficulty is not None:
            clauses.append("difficulty = ?")
            params.append(difficulty)
        if level is not None:
            clauses.append("level = ?")
            params.append(level)
        if source_type is not None:
            clauses.append("source_type = ?")
            params.append(source_type)
        if reviewed is not None:
            clauses.append("reviewed = ?")
            params.append(1 if reviewed else 0)

        sql = "SELECT * FROM objects"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY imported_at"
        cur = self._conn.execute(sql, params)
        return [json.loads(row["json"]) for row in cur.fetchall()]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Bank:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
