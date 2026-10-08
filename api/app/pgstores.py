"""W3b — Postgres (Neon) implementations of every store, behind the same protocols.

Selected when ``EXAM_DATABASE_URL`` is set; otherwise the SQLite stores are used (local
development, the ``mathgen`` CLI and the test suite). Each class passes the identical contract
tests as its SQLite sibling, including tenant isolation: ``owner_id`` leads every key and
filters every query, and a foreign row is indistinguishable from a missing one.

Connections come from a small pool. ``prepare_threshold=None`` keeps this safe behind Neon's
pgbouncer pooler (transaction mode), where server-side prepared statements do not survive.
Schema creation is idempotent and serialised with an advisory lock so several instances
booting together cannot race.
"""

from __future__ import annotations

import os
import secrets
import uuid
from datetime import UTC, datetime
from functools import lru_cache

import psycopg
from exam_engine import canonical
from exam_engine.errors import BankDuplicateId, BankObjectNotFound
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from . import usage
from .accounts import SESSION_TTL, Profile, hash_token
from .assets import AssetNotFound
from .docstore import DocumentNotFound, VersionConflict

_DDL = """
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  title TEXT NOT NULL,
  document JSONB NOT NULL,
  total_marks INTEGER NOT NULL,
  version INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS documents_owner ON documents(owner_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS assets (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  mime TEXT NOT NULL,
  filename TEXT NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  size INTEGER NOT NULL,
  data BYTEA NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS assets_owner ON assets(owner_id);

CREATE TABLE IF NOT EXISTS objects (
  owner_id TEXT NOT NULL,
  id TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  source_type TEXT NOT NULL,
  topic TEXT,
  level TEXT,
  difficulty TEXT,
  created_by TEXT NOT NULL,
  reviewed BOOLEAN NOT NULL DEFAULT FALSE,
  imported_at TIMESTAMPTZ NOT NULL,
  json JSONB NOT NULL,
  PRIMARY KEY (owner_id, id)
);
CREATE INDEX IF NOT EXISTS objects_owner_imported ON objects(owner_id, imported_at);

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT,
  email_verified BOOLEAN NOT NULL DEFAULT FALSE,
  name TEXT,
  created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS users_email ON users(email);
CREATE TABLE IF NOT EXISTS identities (
  provider TEXT NOT NULL,
  subject TEXT NOT NULL,
  user_id TEXT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (provider, subject)
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS export_events (
  id BIGSERIAL PRIMARY KEY,
  owner_id TEXT NOT NULL,
  at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS export_events_owner ON export_events(owner_id, at);
"""

_SCHEMA_LOCK = 727274


class Database:
    """A connection pool plus the (idempotent) schema. ``schema`` isolates test runs."""

    def __init__(self, url: str, *, schema: str | None = None):
        self.url = url
        self.schema = schema
        kwargs: dict = {"row_factory": dict_row, "prepare_threshold": None}
        if schema:
            with psycopg.connect(url, autocommit=True) as conn:
                conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
            kwargs["options"] = f"-c search_path={schema}"
        self.pool = ConnectionPool(
            url,
            min_size=1,
            max_size=int(os.environ.get("EXAM_DB_POOL_MAX", "5")),
            kwargs=kwargs,
            open=True,
        )
        with self.pool.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (_SCHEMA_LOCK,))
            conn.execute(_DDL)

    def connection(self):
        return self.pool.connection()

    def close(self) -> None:
        self.pool.close()

    def drop_schema(self) -> None:
        assert self.schema, "refusing to drop the default schema"
        self.pool.close()
        with psycopg.connect(self.url, autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{self.schema}" CASCADE')


@lru_cache(maxsize=2)
def get_database(url: str) -> Database:
    return Database(url)


def database_url() -> str | None:
    return os.environ.get("EXAM_DATABASE_URL") or None


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _now() -> datetime:
    return datetime.now(UTC)


# --- documents ---------------------------------------------------------------------------


def _doc_record(row: dict, *, with_document: bool = True) -> dict:
    rec = {
        "id": row["id"],
        "title": row["title"],
        "total_marks": row["total_marks"],
        "version": row["version"],
        "created_at": _iso(row["created_at"]),
        "updated_at": _iso(row["updated_at"]),
    }
    if with_document:
        rec["document"] = row["document"]
    return rec


class PgDocumentStore:
    def __init__(self, db: Database):
        self.db = db

    def create(self, owner_id: str, document: dict, total_marks: int) -> dict:
        doc_id, now = str(uuid.uuid4()), _now()
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO documents VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (doc_id, owner_id, document["title"], Jsonb(document), total_marks, 1, now, now),
            )
        return self.get(owner_id, doc_id)

    def get(self, owner_id: str, doc_id: str) -> dict:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = %s AND owner_id = %s", (doc_id, owner_id)
            ).fetchone()
        if row is None:
            raise DocumentNotFound(doc_id)
        return _doc_record(row)

    def list(self, owner_id: str) -> list[dict]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM documents WHERE owner_id = %s ORDER BY updated_at DESC",
                (owner_id,),
            ).fetchall()
        return [_doc_record(r, with_document=False) for r in rows]

    def save(
        self, owner_id: str, doc_id: str, document: dict, total_marks: int, base_version: int
    ) -> dict:
        with self.db.connection() as conn:
            # Atomic compare-and-set: owner and version are in the WHERE.
            cur = conn.execute(
                "UPDATE documents SET title=%s, document=%s, total_marks=%s, "
                "version=version+1, updated_at=%s WHERE id=%s AND owner_id=%s AND version=%s",
                (
                    document["title"],
                    Jsonb(document),
                    total_marks,
                    _now(),
                    doc_id,
                    owner_id,
                    base_version,
                ),
            )
            if cur.rowcount == 0:
                row = conn.execute(
                    "SELECT version FROM documents WHERE id=%s AND owner_id=%s", (doc_id, owner_id)
                ).fetchone()
                if row is None:
                    raise DocumentNotFound(doc_id)
                raise VersionConflict(row["version"])
        return self.get(owner_id, doc_id)

    def delete(self, owner_id: str, doc_id: str) -> None:
        with self.db.connection() as conn:
            cur = conn.execute(
                "DELETE FROM documents WHERE id=%s AND owner_id=%s", (doc_id, owner_id)
            )
            if cur.rowcount == 0:
                raise DocumentNotFound(doc_id)

    def erase_owner(self, owner_id: str) -> int:
        with self.db.connection() as conn:
            return conn.execute("DELETE FROM documents WHERE owner_id=%s", (owner_id,)).rowcount


# --- assets ------------------------------------------------------------------------------


def _asset(row: dict) -> dict:
    return {
        "id": row["id"],
        "mime": row["mime"],
        "filename": row["filename"],
        "width": row["width"],
        "height": row["height"],
        "bytes": row["size"],
        "data": bytes(row["data"]),
    }


class PgAssetStore:
    def __init__(self, db: Database):
        self.db = db

    def put(
        self, owner_id: str, data: bytes, mime: str, filename: str, size: tuple[int, int]
    ) -> dict:
        asset_id = uuid.uuid4().hex
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO assets VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (asset_id, owner_id, mime, filename, size[0], size[1], len(data), data, _now()),
            )
        return {
            "id": asset_id,
            "mime": mime,
            "width": size[0],
            "height": size[1],
            "bytes": len(data),
        }

    def get(self, owner_id: str, asset_id: str) -> dict:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM assets WHERE id = %s AND owner_id = %s", (asset_id, owner_id)
            ).fetchone()
        if row is None:
            raise AssetNotFound(asset_id)
        return _asset(row)

    def delete(self, owner_id: str, asset_id: str) -> None:
        with self.db.connection() as conn:
            cur = conn.execute(
                "DELETE FROM assets WHERE id = %s AND owner_id = %s", (asset_id, owner_id)
            )
            if cur.rowcount == 0:
                raise AssetNotFound(asset_id)

    def usage(self, owner_id: str) -> int:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(size), 0) AS total FROM assets WHERE owner_id = %s",
                (owner_id,),
            ).fetchone()
        return int(row["total"])

    def owned(self, owner_id: str, asset_ids: list[str]) -> set[str]:
        if not asset_ids:
            return set()
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT id FROM assets WHERE owner_id = %s AND id = ANY(%s)",
                (owner_id, list(asset_ids)),
            ).fetchall()
        return {r["id"] for r in rows}

    def export_all(self, owner_id: str) -> list[dict]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM assets WHERE owner_id = %s ORDER BY created_at, id", (owner_id,)
            ).fetchall()
        return [_asset(r) for r in rows]

    def erase_owner(self, owner_id: str) -> int:
        with self.db.connection() as conn:
            return conn.execute("DELETE FROM assets WHERE owner_id = %s", (owner_id,)).rowcount


# --- bank --------------------------------------------------------------------------------


class PgBank:
    """The owner's question bank (same surface the API uses from the engine's SQLite ``Bank``)."""

    def __init__(self, db: Database, owner_id: str):
        self.db = db
        self.owner_id = owner_id

    def _row(self, conn, obj_id: str) -> dict | None:
        return conn.execute(
            "SELECT * FROM objects WHERE owner_id = %s AND id = %s", (self.owner_id, obj_id)
        ).fetchone()

    def add(self, obj: dict, *, overwrite: bool = False) -> dict:
        obj = canonical.load(dict(obj))
        with self.db.connection() as conn:
            existing = self._row(conn, obj["id"])
            if existing is not None and not overwrite:
                raise BankDuplicateId(obj["id"])
            if not obj["provenance"].get("created_at"):
                obj["provenance"]["created_at"] = _now().isoformat()
                obj = canonical.load(obj)
            imported_at = existing["imported_at"] if existing is not None else _now()
            checks = obj.get("validation", {}).get("checks", {})
            conn.execute(
                """
                INSERT INTO objects (owner_id, id, schema_version, source_type, topic, level,
                    difficulty, created_by, reviewed, imported_at, json)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (owner_id, id) DO UPDATE SET
                    schema_version = EXCLUDED.schema_version,
                    source_type = EXCLUDED.source_type, topic = EXCLUDED.topic,
                    level = EXCLUDED.level, difficulty = EXCLUDED.difficulty,
                    created_by = EXCLUDED.created_by, reviewed = EXCLUDED.reviewed,
                    json = EXCLUDED.json
                """,
                (
                    self.owner_id,
                    obj["id"],
                    obj["schema_version"],
                    obj["source_type"],
                    obj.get("syllabus", {}).get("topic"),
                    obj.get("syllabus", {}).get("level"),
                    obj.get("cognitive", {}).get("difficulty"),
                    obj["provenance"]["created_by"],
                    bool(checks.get("human_reviewed")),
                    imported_at,
                    Jsonb(obj),
                ),
            )
        return obj

    def update(self, obj: dict) -> dict:
        """Overwrite an existing row with a hand-corrected object (bumps ``provenance.version``)."""
        existing = self.get(obj["id"])
        obj = dict(obj)
        obj["provenance"] = dict(obj["provenance"])
        obj["provenance"]["version"] = existing["provenance"].get("version", 1) + 1
        return self.add(obj, overwrite=True)

    def set_reviewed(self, obj_id: str, reviewed: bool) -> dict:
        """Set ``checks.human_reviewed`` (ADR-0019's review action, and its undo); idempotent."""
        obj = self.get(obj_id)
        checks = obj.setdefault("validation", {}).setdefault("checks", {})
        if bool(checks.get("human_reviewed")) == reviewed:
            return obj
        checks["human_reviewed"] = reviewed
        return self.update(obj)

    def mark_reviewed(self, obj_id: str) -> dict:
        """Flip ``checks.human_reviewed`` to true (ADR-0019's review action)."""
        return self.set_reviewed(obj_id, True)

    def get(self, obj_id: str) -> dict:
        with self.db.connection() as conn:
            row = self._row(conn, obj_id)
        if row is None:
            raise BankObjectNotFound(obj_id)
        return row["json"]

    def search(
        self,
        *,
        topic: str | None = None,
        difficulty: str | None = None,
        level: str | None = None,
        source_type: str | None = None,
        reviewed: bool | None = None,
    ) -> list[dict]:
        clauses = ["owner_id = %s"]
        params: list[object] = [self.owner_id]
        for column, value in (
            ("topic", topic),
            ("difficulty", difficulty),
            ("level", level),
            ("source_type", source_type),
        ):
            if value is not None:
                clauses.append(f"{column} = %s")
                params.append(value)
        if reviewed is not None:
            clauses.append("reviewed = %s")
            params.append(bool(reviewed))
        sql = (
            "SELECT json FROM objects WHERE "  # noqa: S608 - columns are a fixed whitelist
            + " AND ".join(clauses)
            + " ORDER BY imported_at, id"
        )
        with self.db.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [r["json"] for r in rows]

    def erase(self) -> int:
        with self.db.connection() as conn:
            return conn.execute(
                "DELETE FROM objects WHERE owner_id = %s", (self.owner_id,)
            ).rowcount

    def close(self) -> None:  # the pool is shared; nothing per-bank to release
        pass


# --- accounts ----------------------------------------------------------------------------


def _user(row: dict) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "email_verified": bool(row["email_verified"]),
        "name": row["name"],
    }


class PgAccountStore:
    def __init__(self, db: Database):
        self.db = db

    def login(self, profile: Profile) -> dict:
        email = profile.email.strip().lower() if profile.email else None
        verified = bool(email and profile.email_verified)
        now = _now()
        with self.db.connection() as conn:
            # One identity is resolved at a time, so two first logins cannot create two users.
            conn.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (f"{profile.provider}:{profile.subject}",),
            )
            row = conn.execute(
                "SELECT u.* FROM identities i JOIN users u ON u.id = i.user_id "
                "WHERE i.provider = %s AND i.subject = %s",
                (profile.provider, profile.subject),
            ).fetchone()
            if row is not None:
                if verified and not row["email_verified"]:
                    row = conn.execute(
                        "UPDATE users SET email = %s, email_verified = TRUE WHERE id = %s "
                        "RETURNING *",
                        (email, row["id"]),
                    ).fetchone()
                return _user(row)

            target = None
            if verified:  # link ONLY through a verified email on both sides
                conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"email:{email}",))
                target = conn.execute(
                    "SELECT * FROM users WHERE email = %s AND email_verified ORDER BY created_at "
                    "LIMIT 1",
                    (email,),
                ).fetchone()
            if target is None:
                target = conn.execute(
                    "INSERT INTO users VALUES (%s,%s,%s,%s,%s) RETURNING *",
                    (str(uuid.uuid4()), email, verified, profile.name, now),
                ).fetchone()
            conn.execute(
                "INSERT INTO identities VALUES (%s,%s,%s,%s)",
                (profile.provider, profile.subject, target["id"], now),
            )
            return _user(target)

    def get_user(self, user_id: str) -> dict | None:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()
        return _user(row) if row else None

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        now = _now()
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO sessions VALUES (%s,%s,%s,%s)",
                (hash_token(token), user_id, now, now + SESSION_TTL),
            )
        return token

    def user_for_session(self, token: str) -> dict | None:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
                "WHERE s.token_hash = %s AND s.expires_at > %s",
                (hash_token(token), _session_now()),
            ).fetchone()
        return _user(row) if row else None

    def delete_session(self, token: str) -> None:
        with self.db.connection() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = %s", (hash_token(token),))

    def delete_user(self, user_id: str) -> None:
        with self.db.connection() as conn:  # one transaction: the FK order is sessions, ids, user
            conn.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
            conn.execute("DELETE FROM identities WHERE user_id = %s", (user_id,))
            conn.execute("DELETE FROM users WHERE id = %s", (user_id,))


def _session_now() -> datetime:
    from . import accounts

    return accounts._now()


# --- export ledger -----------------------------------------------------------------------


class PgUsageLedger:
    def __init__(self, db: Database):
        self.db = db

    def consume(self, owner_id: str, limits: usage.Limits) -> usage.Allowance:
        now = usage._now()
        with self.db.connection() as conn:
            # Serialise one account's consumers: parallel requests cannot all slip under.
            conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"export:{owner_id}",))
            conn.execute("DELETE FROM export_events WHERE at < %s", (now - usage.DAY_S,))
            for reason, window, limit in (
                ("minute", usage.MINUTE_S, limits.per_minute),
                ("day", usage.DAY_S, limits.per_day),
            ):
                if limit <= 0:
                    continue
                rows = conn.execute(
                    "SELECT at FROM export_events WHERE owner_id = %s AND at > %s ORDER BY at",
                    (owner_id, now - window),
                ).fetchall()
                if len(rows) >= limit:
                    blocking = rows[len(rows) - limit]["at"]
                    wait = int(blocking + window - now) + 1
                    return usage.Allowance(False, max(1, wait), reason, None)
            row = conn.execute(
                "INSERT INTO export_events (owner_id, at) VALUES (%s, %s) RETURNING id",
                (owner_id, now),
            ).fetchone()
        return usage.Allowance(True, 0, "", int(row["id"]))

    def refund(self, ticket: int) -> None:
        with self.db.connection() as conn:
            conn.execute("DELETE FROM export_events WHERE id = %s", (ticket,))

    def erase_owner(self, owner_id: str) -> None:
        with self.db.connection() as conn:
            conn.execute("DELETE FROM export_events WHERE owner_id = %s", (owner_id,))

    def used(self, owner_id: str) -> tuple[int, int]:
        now = usage._now()
        with self.db.connection() as conn:
            day = conn.execute(
                "SELECT COUNT(*) AS n FROM export_events WHERE owner_id = %s AND at > %s",
                (owner_id, now - usage.DAY_S),
            ).fetchone()["n"]
            minute = conn.execute(
                "SELECT COUNT(*) AS n FROM export_events WHERE owner_id = %s AND at > %s",
                (owner_id, now - usage.MINUTE_S),
            ).fetchone()["n"]
        return int(day), int(minute)
