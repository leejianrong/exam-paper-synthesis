"""W3 — accounts and sessions behind an interface (ADR-0022).

Social sign-in only: a user is reached through one or more *identities* (provider + the
provider's own subject id). The same person arriving through a second provider is linked
**only** when both sides carry a *verified* email; an unverified email never links, it makes a
separate account. Sessions are random server-side tokens (stored hashed); the cookie holds
the token, nothing else. ``SqliteAccountStore`` is the first implementation; the Postgres one
(W3b) must pass the same contract tests.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Protocol

SESSION_TTL = timedelta(days=30)

_DDL = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT,
  email_verified INTEGER NOT NULL DEFAULT 0,
  name TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS users_email ON users(email);
CREATE TABLE IF NOT EXISTS identities (
  provider TEXT NOT NULL,
  subject TEXT NOT NULL,
  user_id TEXT NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL,
  PRIMARY KEY (provider, subject)
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
"""


@dataclass(frozen=True)
class Profile:
    """What a provider told us about the person who just signed in."""

    provider: str
    subject: str
    email: str | None
    email_verified: bool
    name: str | None


class AccountStore(Protocol):
    def login(self, profile: Profile) -> dict: ...
    def get_user(self, user_id: str) -> dict | None: ...
    def create_session(self, user_id: str) -> str: ...
    def user_for_session(self, token: str) -> dict | None: ...
    def delete_session(self, token: str) -> None: ...
    def delete_user(self, user_id: str) -> None: ...


def _now() -> datetime:
    return datetime.now(UTC)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def default_path() -> Path:
    env = os.environ.get("EXAM_AUTH_PATH")
    return Path(env) if env else Path.home() / ".exam_engine" / "accounts.sqlite3"


def _user(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "email_verified": bool(row["email_verified"]),
        "name": row["name"],
    }


class SqliteAccountStore:
    def __init__(self, path: Path):
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(_DDL)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def login(self, profile: Profile) -> dict:
        """The user for this identity: existing, linked by verified email, or new."""
        email = profile.email.strip().lower() if profile.email else None
        verified = bool(email and profile.email_verified)
        now = _now().isoformat()
        with closing(self._connect()) as conn, conn:
            row = conn.execute(
                "SELECT u.* FROM identities i JOIN users u ON u.id = i.user_id "
                "WHERE i.provider = ? AND i.subject = ?",
                (profile.provider, profile.subject),
            ).fetchone()
            if row is not None:
                if verified and not row["email_verified"]:
                    conn.execute(
                        "UPDATE users SET email = ?, email_verified = 1 WHERE id = ?",
                        (email, row["id"]),
                    )
                    row = conn.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()
                return _user(row)

            target = None
            if verified:  # link ONLY through a verified email on both sides
                target = conn.execute(
                    "SELECT * FROM users WHERE email = ? AND email_verified = 1", (email,)
                ).fetchone()
            if target is None:
                user_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO users VALUES (?,?,?,?,?)",
                    (user_id, email, int(verified), profile.name, now),
                )
                target = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            conn.execute(
                "INSERT INTO identities VALUES (?,?,?,?)",
                (profile.provider, profile.subject, target["id"], now),
            )
            return _user(target)

    def get_user(self, user_id: str) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _user(row) if row else None

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        now = _now()
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO sessions VALUES (?,?,?,?)",
                (hash_token(token), user_id, now.isoformat(), (now + SESSION_TTL).isoformat()),
            )
        return token

    def user_for_session(self, token: str) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT u.*, s.expires_at FROM sessions s JOIN users u ON u.id = s.user_id "
                "WHERE s.token_hash = ?",
                (hash_token(token),),
            ).fetchone()
        if row is None or datetime.fromisoformat(row["expires_at"]) <= _now():
            return None
        return _user(row)

    def delete_session(self, token: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_token(token),))

    def delete_user(self, user_id: str) -> None:
        """Remove the account: its sessions, linked identities and the user row."""
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM identities WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


@lru_cache(maxsize=8)
def _store_at(path: Path) -> SqliteAccountStore:
    return SqliteAccountStore(path)


def get_account_store() -> AccountStore:
    """FastAPI dependency: the configured store (env read per call so tests can redirect it)."""
    from . import pgstores

    if url := pgstores.database_url():
        return pgstores.PgAccountStore(pgstores.get_database(url))
    return _store_at(default_path())
