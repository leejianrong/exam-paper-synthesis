"""W3c — per-account export allowance (ADR-0022: free, with a limit per account).

PDF export runs headless Chromium, the one expensive thing the product does, so each account
gets a rolling allowance: ``EXAM_EXPORT_LIMIT_PER_DAY`` (default 30) over the last 24 hours and
``EXAM_EXPORT_LIMIT_PER_MINUTE`` (default 5) over the last minute; ``0`` means unlimited. The
ledger consumes atomically — a burst of parallel requests cannot all slip under the limit — and
an export that fails is refunded. ``SqliteUsageLedger`` is the first implementation; W3b's
Postgres one must pass the same contract tests.
"""

from __future__ import annotations

import os
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

DAY_S = 24 * 60 * 60
MINUTE_S = 60

_DDL = """
CREATE TABLE IF NOT EXISTS export_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_id TEXT NOT NULL,
  at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS export_events_owner ON export_events(owner_id, at);
"""


@dataclass(frozen=True)
class Limits:
    per_day: int
    per_minute: int


@dataclass(frozen=True)
class Allowance:
    """Result of trying to consume one export. ``ticket`` is what :meth:`refund` takes."""

    allowed: bool
    retry_after: int  # seconds until the blocking window frees a slot (0 when allowed)
    reason: str  # "" | "minute" | "day"
    ticket: int | None


class UsageLedger(Protocol):
    def consume(self, owner_id: str, limits: Limits) -> Allowance: ...
    def refund(self, ticket: int) -> None: ...
    def used(self, owner_id: str) -> tuple[int, int]: ...  # (last 24 h, last minute)


def _now() -> float:
    return time.time()


def limits_from_env() -> Limits:
    def num(name: str, default: int) -> int:
        try:
            return max(0, int(os.environ.get(name, default)))
        except ValueError:
            return default

    return Limits(num("EXAM_EXPORT_LIMIT_PER_DAY", 30), num("EXAM_EXPORT_LIMIT_PER_MINUTE", 5))


def default_path() -> Path:
    env = os.environ.get("EXAM_USAGE_PATH")
    return Path(env) if env else Path.home() / ".exam_engine" / "usage.sqlite3"


class SqliteUsageLedger:
    def __init__(self, path: Path):
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(_DDL)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def consume(self, owner_id: str, limits: Limits) -> Allowance:
        now = _now()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")  # serialise concurrent consumers
            try:
                conn.execute("DELETE FROM export_events WHERE at < ?", (now - DAY_S,))
                for reason, window, limit in (
                    ("minute", MINUTE_S, limits.per_minute),
                    ("day", DAY_S, limits.per_day),
                ):
                    if limit <= 0:
                        continue
                    rows = conn.execute(
                        "SELECT at FROM export_events WHERE owner_id = ? AND at > ? ORDER BY at",
                        (owner_id, now - window),
                    ).fetchall()
                    if len(rows) >= limit:
                        # the window frees a slot when the (len-limit+1)-th oldest event ages out
                        blocking = rows[len(rows) - limit]["at"]
                        wait = int(blocking + window - now) + 1
                        conn.execute("ROLLBACK")
                        return Allowance(False, max(1, wait), reason, None)
                cur = conn.execute(
                    "INSERT INTO export_events (owner_id, at) VALUES (?, ?)", (owner_id, now)
                )
                ticket = cur.lastrowid
                conn.execute("COMMIT")
                return Allowance(True, 0, "", ticket)
            except BaseException:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

    def refund(self, ticket: int) -> None:
        with closing(self._connect()) as conn:
            conn.execute("DELETE FROM export_events WHERE id = ?", (ticket,))

    def used(self, owner_id: str) -> tuple[int, int]:
        now = _now()
        with closing(self._connect()) as conn:
            day = conn.execute(
                "SELECT COUNT(*) FROM export_events WHERE owner_id = ? AND at > ?",
                (owner_id, now - DAY_S),
            ).fetchone()[0]
            minute = conn.execute(
                "SELECT COUNT(*) FROM export_events WHERE owner_id = ? AND at > ?",
                (owner_id, now - MINUTE_S),
            ).fetchone()[0]
        return int(day), int(minute)


@lru_cache(maxsize=8)
def _ledger_at(path: Path) -> SqliteUsageLedger:
    return SqliteUsageLedger(path)


def get_ledger() -> UsageLedger:
    """The configured ledger (env read per call so tests can redirect it)."""
    from . import pgstores

    if url := pgstores.database_url():
        return pgstores.PgUsageLedger(pgstores.get_database(url))
    return _ledger_at(default_path())
