"""O1 — per-account settings (EXA-125, docs/planning/editor/ORGANIZE-SHAPING.md).

A small key/value record per owner, stored server-side so it follows the teacher across
devices. Only known keys are accepted (``DEFAULTS``); reads merge what is stored over the
defaults, so a new setting needs no migration. ``SqliteSettingsStore`` keeps its table in the
documents database (``EXAM_DOCS_PATH``); ``pgstores.PgSettingsStore`` is its Postgres sibling
and passes the same contract tests. Tenant-scoped like every store: ``owner_id`` keys each row.
"""

from __future__ import annotations

import json
import sqlite3
import unicodedata
from contextlib import closing
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from exam_engine.document import KEY_STYLES
from exam_engine.paper import LEVELS

from .docstore import default_path

# Every setting and its default. The Classic generator (the original Generate + tray page) is
# hidden unless a teacher turns it on. ``answer_key_style`` (EXA-159) is the key a new paper
# starts with: the school key, or worked solutions; a saved paper keeps its own. The other new
# paper defaults (EXA-169): the cover's school name, the level (stated on the cover and offered
# first in the New dialog; "" = none) and where marks print (the paper's marks_placement).
DEFAULTS: dict[str, bool | str] = {
    "classic_generator": False,
    "answer_key_style": "school",
    "school_name": "",
    "default_level": "",
    "marks_placement": "answer",
}

# A text setting takes only these values.
CHOICES: dict[str, tuple[str, ...]] = {
    "answer_key_style": KEY_STYLES,
    "default_level": ("", *LEVELS),
    "marks_placement": ("answer", "question", "both"),
}

# A free-text setting's limit: the cover field's own (``school`` in document.schema.json).
MAX_LENGTH: dict[str, int] = {"school_name": 120}

_DDL = """
CREATE TABLE IF NOT EXISTS settings (
  owner_id TEXT PRIMARY KEY,
  data TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""


class UnknownSetting(ValueError):
    pass


def merged(stored: dict | None) -> dict:
    """The defaults overlaid with the stored known keys (unknown stored keys are dropped)."""
    out = dict(DEFAULTS)
    for k, v in (stored or {}).items():
        if k in DEFAULTS and _valid(k, v):
            out[k] = v
    return out


def _valid(key: str, value: object) -> bool:
    if not isinstance(value, type(DEFAULTS[key])):
        return False
    if isinstance(value, str) and key in MAX_LENGTH:
        return len(value) <= MAX_LENGTH[key] and not _has_control(value)
    return value in CHOICES.get(key, (value,))


# Bidirectional formatting controls (Cf): they can reorder how the rest of a cover line reads.
_BIDI_CONTROLS = frozenset(
    "\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
)


def _has_control(text: str) -> bool:
    """Whether ``text`` is more than one plain line: control characters (Cc, which includes
    C1 such as U+0085), line and paragraph separators (Zl, Zp) or bidi controls."""
    return any(unicodedata.category(c) in ("Cc", "Zl", "Zp") or c in _BIDI_CONTROLS for c in text)


def check_patch(patch: dict) -> dict:
    """``patch`` restricted to known keys with values of the default's type, else raise. Free
    text comes back trimmed."""
    out = {}
    for k, v in patch.items():
        if k not in DEFAULTS:
            raise UnknownSetting(f"unknown setting {k!r}")
        if not isinstance(v, type(DEFAULTS[k])):
            raise UnknownSetting(f"{k!r} must be a {type(DEFAULTS[k]).__name__}")
        if isinstance(v, str) and k in MAX_LENGTH:
            v = v.strip()
            if len(v) > MAX_LENGTH[k]:
                raise UnknownSetting(f"{k!r} must be at most {MAX_LENGTH[k]} characters")
            if _has_control(v):
                raise UnknownSetting(f"{k!r} must be one line of text")
        elif not _valid(k, v):
            raise UnknownSetting(f"{k!r} must be one of {', '.join(map(repr, CHOICES[k]))}")
        out[k] = v
    return out


class SettingsStore(Protocol):
    def get(self, owner_id: str) -> dict: ...
    def update(self, owner_id: str, patch: dict) -> dict: ...
    def erase_owner(self, owner_id: str) -> None: ...


class SqliteSettingsStore:
    def __init__(self, path: Path):
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(_DDL)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._path), timeout=10)

    def _stored(self, conn: sqlite3.Connection, owner_id: str) -> dict:
        row = conn.execute("SELECT data FROM settings WHERE owner_id = ?", (owner_id,)).fetchone()
        return json.loads(row[0]) if row else {}

    def get(self, owner_id: str) -> dict:
        with closing(self._connect()) as conn:
            return merged(self._stored(conn, owner_id))

    def update(self, owner_id: str, patch: dict) -> dict:
        patch = check_patch(patch)
        with closing(self._connect()) as conn, conn:
            data = merged(self._stored(conn, owner_id)) | patch
            conn.execute(
                "INSERT INTO settings VALUES (?,?,?) ON CONFLICT(owner_id) DO UPDATE "
                "SET data = excluded.data, updated_at = excluded.updated_at",
                (owner_id, json.dumps(data), datetime.now(UTC).isoformat()),
            )
        return merged(data)

    def erase_owner(self, owner_id: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM settings WHERE owner_id = ?", (owner_id,))


@lru_cache(maxsize=8)
def _store_at(path: Path) -> SqliteSettingsStore:
    return SqliteSettingsStore(path)


def get_settings_store() -> SettingsStore:
    """FastAPI dependency: Postgres when ``EXAM_DATABASE_URL`` is set, else SQLite."""
    from . import pgstores  # lazy: SQLite-only runs need no Postgres driver at import

    if url := pgstores.database_url():
        return pgstores.PgSettingsStore(pgstores.get_database(url))
    return _store_at(default_path())
