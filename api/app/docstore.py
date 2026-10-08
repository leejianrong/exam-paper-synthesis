"""W1b — tenant-scoped document storage behind an interface (ADR-0022).

Every method takes ``owner_id`` first and every query filters on it; a document owned by
someone else is indistinguishable from a missing one (``DocumentNotFound``), so ids can't
be probed. ``SqliteDocumentStore`` is the W1 implementation; W3 adds a Postgres one
behind the same protocol and must pass the identical contract tests.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Protocol

_DDL = """
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  title TEXT NOT NULL,
  document TEXT NOT NULL,
  total_marks INTEGER NOT NULL,
  version INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS documents_owner ON documents(owner_id, updated_at DESC);
"""


class DocumentNotFound(Exception):
    """No such document for this owner (also raised for another owner's document)."""


class VersionConflict(Exception):
    """``base_version`` does not match the stored version (a stale save)."""

    def __init__(self, current: int):
        self.current = current
        super().__init__(f"stored version is {current}")


class DocumentStore(Protocol):
    def create(self, owner_id: str, document: dict, total_marks: int) -> dict: ...
    def get(self, owner_id: str, doc_id: str) -> dict: ...
    def list(self, owner_id: str) -> list[dict]: ...
    def save(
        self, owner_id: str, doc_id: str, document: dict, total_marks: int, base_version: int
    ) -> dict: ...
    def delete(self, owner_id: str, doc_id: str) -> None: ...


def _now() -> str:
    return datetime.now(UTC).isoformat()


def default_path() -> Path:
    env = os.environ.get("EXAM_DOCS_PATH")
    return Path(env) if env else Path.home() / ".exam_engine" / "documents.sqlite3"


def _record(row: sqlite3.Row, *, with_document: bool = True) -> dict:
    rec = {
        "id": row["id"],
        "title": row["title"],
        "total_marks": row["total_marks"],
        "version": row["version"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    if with_document:
        rec["document"] = json.loads(row["document"])
    return rec


class SqliteDocumentStore:
    """stdlib-sqlite3 store; one short-lived connection per call (thread-safe by design)."""

    def __init__(self, path: Path):
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(_DDL)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, owner_id: str, document: dict, total_marks: int) -> dict:
        doc_id, now = str(uuid.uuid4()), _now()
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
                (
                    doc_id,
                    owner_id,
                    document["title"],
                    json.dumps(document, ensure_ascii=False),
                    total_marks,
                    1,
                    now,
                    now,
                ),
            )
        return self.get(owner_id, doc_id)

    def get(self, owner_id: str, doc_id: str) -> dict:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ? AND owner_id = ?", (doc_id, owner_id)
            ).fetchone()
        if row is None:
            raise DocumentNotFound(doc_id)
        return _record(row)

    def list(self, owner_id: str) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM documents WHERE owner_id = ? ORDER BY updated_at DESC", (owner_id,)
            ).fetchall()
        return [_record(r, with_document=False) for r in rows]

    def save(
        self, owner_id: str, doc_id: str, document: dict, total_marks: int, base_version: int
    ) -> dict:
        with closing(self._connect()) as conn, conn:
            # Atomic compare-and-set: the WHERE carries owner and version, so a stale or
            # foreign save changes nothing.
            cur = conn.execute(
                "UPDATE documents SET title=?, document=?, total_marks=?, version=version+1, "
                "updated_at=? WHERE id=? AND owner_id=? AND version=?",
                (
                    document["title"],
                    json.dumps(document, ensure_ascii=False),
                    total_marks,
                    _now(),
                    doc_id,
                    owner_id,
                    base_version,
                ),
            )
            if cur.rowcount == 0:
                row = conn.execute(
                    "SELECT version FROM documents WHERE id=? AND owner_id=?", (doc_id, owner_id)
                ).fetchone()
                if row is None:
                    raise DocumentNotFound(doc_id)
                raise VersionConflict(row["version"])
        return self.get(owner_id, doc_id)

    def delete(self, owner_id: str, doc_id: str) -> None:
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "DELETE FROM documents WHERE id=? AND owner_id=?", (doc_id, owner_id)
            )
            if cur.rowcount == 0:
                raise DocumentNotFound(doc_id)


@lru_cache(maxsize=8)
def _store_at(path: Path) -> SqliteDocumentStore:
    return SqliteDocumentStore(path)


def get_store() -> DocumentStore:
    """FastAPI dependency: the configured store (env read per call so tests can redirect it)."""
    return _store_at(default_path())
