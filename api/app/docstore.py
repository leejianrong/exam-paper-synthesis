"""W1b — tenant-scoped document storage behind an interface (ADR-0022).

Every method takes ``owner_id`` first and every query filters on it; a document owned by
someone else is indistinguishable from a missing one (``DocumentNotFound``), so ids can't
be probed. ``SqliteDocumentStore`` is the W1 implementation; W3 adds a Postgres one
behind the same protocol and must pass the identical contract tests.
"""

from __future__ import annotations

import builtins
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
CREATE TABLE IF NOT EXISTS folders (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS folders_owner ON folders(owner_id);
"""
# O2: run after the idempotent ``folder_id`` column add (an older file has no such column).
_DDL_AFTER_COLUMNS = """
CREATE INDEX IF NOT EXISTS documents_owner_folder ON documents(owner_id, folder_id);
"""
_DOC_COLUMNS = (
    "id, owner_id, title, document, total_marks, version, created_at, updated_at, folder_id"
)
FOLDER_NAME_MAX = 80


class DocumentNotFound(Exception):
    """No such document for this owner (also raised for another owner's document)."""


class VersionConflict(Exception):
    """``base_version`` does not match the stored version (a stale save)."""

    def __init__(self, current: int):
        self.current = current
        super().__init__(f"stored version is {current}")


class FolderNotFound(Exception):
    """No such folder for this owner (also raised for another owner's folder)."""


class InvalidFolderName(ValueError):
    """A folder name must be 1-80 characters once trimmed."""


def clean_folder_name(name: str) -> str:
    """O2: trimmed, 1-80 characters (duplicates are allowed)."""
    # whitespace runs (incl. newlines and tabs) become one space; other control characters go
    cleaned = " ".join(name.split()) if isinstance(name, str) else ""
    cleaned = "".join(ch for ch in cleaned if ch.isprintable())
    if not 1 <= len(cleaned) <= FOLDER_NAME_MAX:
        raise InvalidFolderName(f"a folder name is 1-{FOLDER_NAME_MAX} characters")
    return cleaned


class DocumentStore(Protocol):
    def create(
        self, owner_id: str, document: dict, total_marks: int, folder_id: str | None = None
    ) -> dict: ...
    def get(self, owner_id: str, doc_id: str) -> dict: ...
    def list(self, owner_id: str) -> list[dict]: ...
    def save(
        self, owner_id: str, doc_id: str, document: dict, total_marks: int, base_version: int
    ) -> dict: ...
    def delete(self, owner_id: str, doc_id: str) -> None: ...
    def erase_owner(self, owner_id: str) -> int: ...
    # O2 folders: owner-scoped; a foreign folder is a FolderNotFound.
    def move(self, owner_id: str, doc_id: str, folder_id: str | None) -> dict: ...
    def create_folder(self, owner_id: str, name: str) -> dict: ...
    def list_folders(self, owner_id: str) -> builtins.list[dict]: ...
    def rename_folder(self, owner_id: str, folder_id: str, name: str) -> dict: ...
    def delete_folder(self, owner_id: str, folder_id: str) -> None: ...


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
        "folder_id": row["folder_id"],
    }
    if with_document:
        rec["document"] = json.loads(row["document"])
    return rec


def _folder(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "papers": row["papers"],
    }


_FOLDERS_SQL = (
    "SELECT f.id, f.name, f.created_at, f.updated_at, COUNT(d.id) AS papers FROM folders f "
    "LEFT JOIN documents d ON d.folder_id = f.id AND d.owner_id = f.owner_id "
    "WHERE f.owner_id = ? {extra}GROUP BY f.id, f.name, f.created_at, f.updated_at "
    "ORDER BY lower(f.name), f.created_at, f.id"
)


class SqliteDocumentStore:
    """stdlib-sqlite3 store; one short-lived connection per call (thread-safe by design)."""

    def __init__(self, path: Path):
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(_DDL)
            # O2: no migration tool — add the nullable column when an older file lacks it.
            columns = {r["name"] for r in conn.execute("PRAGMA table_info(documents)")}
            if "folder_id" not in columns:
                try:
                    conn.execute("ALTER TABLE documents ADD COLUMN folder_id TEXT")
                except sqlite3.OperationalError as e:  # another process added it first
                    if "duplicate column" not in str(e):
                        raise
            conn.executescript(_DDL_AFTER_COLUMNS)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def create(
        self, owner_id: str, document: dict, total_marks: int, folder_id: str | None = None
    ) -> dict:
        doc_id, now = str(uuid.uuid4()), _now()
        with closing(self._connect()) as conn, conn:
            if folder_id is not None:
                self._owned_folder_or_raise(conn, owner_id, folder_id)
            conn.execute(
                f"INSERT INTO documents ({_DOC_COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    doc_id,
                    owner_id,
                    document["title"],
                    json.dumps(document, ensure_ascii=False),
                    total_marks,
                    1,
                    now,
                    now,
                    folder_id,
                ),
            )
        return self.get(owner_id, doc_id)

    @staticmethod
    def _owned_folder_or_raise(conn: sqlite3.Connection, owner_id: str, folder_id: str) -> None:
        # Take the write lock first so the folder cannot be deleted between this check and
        # the write that files the paper in it (``with conn`` commits or rolls back).
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT 1 FROM folders WHERE id = ? AND owner_id = ?", (folder_id, owner_id)
        ).fetchone()
        if row is None:
            raise FolderNotFound(folder_id)

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

    def erase_owner(self, owner_id: str) -> int:
        """Delete every document the owner has (account deletion); returns how many."""
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM folders WHERE owner_id=?", (owner_id,))
            return conn.execute("DELETE FROM documents WHERE owner_id=?", (owner_id,)).rowcount

    # --- O2 folders ------------------------------------------------------------------

    def move(self, owner_id: str, doc_id: str, folder_id: str | None) -> dict:
        """File a paper in a folder (``None`` = unfiled). Content, version and
        ``updated_at`` are untouched: moving is not an edit."""
        with closing(self._connect()) as conn, conn:
            if folder_id is not None:
                self._owned_folder_or_raise(conn, owner_id, folder_id)
            cur = conn.execute(
                "UPDATE documents SET folder_id=? WHERE id=? AND owner_id=?",
                (folder_id, doc_id, owner_id),
            )
            if cur.rowcount == 0:
                raise DocumentNotFound(doc_id)
            row = conn.execute(
                "SELECT * FROM documents WHERE id=? AND owner_id=?", (doc_id, owner_id)
            ).fetchone()
        return _record(row, with_document=False)

    def create_folder(self, owner_id: str, name: str) -> dict:
        folder_id, now, name = str(uuid.uuid4()), _now(), clean_folder_name(name)
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO folders (id, owner_id, name, created_at, updated_at) "
                "VALUES (?,?,?,?,?)",
                (folder_id, owner_id, name, now, now),
            )
        return self._folder(owner_id, folder_id)

    def _folder(self, owner_id: str, folder_id: str) -> dict:
        with closing(self._connect()) as conn:
            row = conn.execute(
                _FOLDERS_SQL.format(extra="AND f.id = ? "), (owner_id, folder_id)
            ).fetchone()
        if row is None:
            raise FolderNotFound(folder_id)
        return _folder(row)

    def list_folders(self, owner_id: str) -> builtins.list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(_FOLDERS_SQL.format(extra=""), (owner_id,)).fetchall()
        return [_folder(r) for r in rows]

    def rename_folder(self, owner_id: str, folder_id: str, name: str) -> dict:
        name = clean_folder_name(name)
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "UPDATE folders SET name=?, updated_at=? WHERE id=? AND owner_id=?",
                (name, _now(), folder_id, owner_id),
            )
            if cur.rowcount == 0:
                raise FolderNotFound(folder_id)
        return self._folder(owner_id, folder_id)

    def delete_folder(self, owner_id: str, folder_id: str) -> None:
        """Delete the folder; its papers become unfiled (never deleted). One transaction."""
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "DELETE FROM folders WHERE id=? AND owner_id=?", (folder_id, owner_id)
            )
            if cur.rowcount == 0:
                raise FolderNotFound(folder_id)
            conn.execute(
                "UPDATE documents SET folder_id=NULL WHERE owner_id=? AND folder_id=?",
                (owner_id, folder_id),
            )


@lru_cache(maxsize=8)
def _store_at(path: Path) -> SqliteDocumentStore:
    return SqliteDocumentStore(path)


def get_store() -> DocumentStore:
    """FastAPI dependency: the configured store (env read per call so tests can redirect it)."""
    from . import pgstores  # lazy: SQLite-only runs need no Postgres driver at import

    if url := pgstores.database_url():
        return pgstores.PgDocumentStore(pgstores.get_database(url))
    return _store_at(default_path())
