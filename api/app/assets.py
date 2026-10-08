"""W2b — owner-scoped image assets behind an interface (ADR-0022).

Same contract shape as the document store: ``owner_id`` first on every method, and another
owner's asset is indistinguishable from a missing one (``AssetNotFound``). W2 keeps the bytes
in SQLite; W3/W4 move them to object storage behind the same protocol and must pass the same
contract tests. ``sniff_image`` is the upload gate: it trusts the bytes, never the filename
or the client's MIME, and accepts PNG and JPEG only.
"""

from __future__ import annotations

import os
import sqlite3
import struct
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Protocol

MAX_ASSET_BYTES = 2 * 1024 * 1024
MAX_SIDE_PX = 4096
MAX_OWNER_BYTES = 50 * 1024 * 1024

_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_PNG_IEND = b"\x00\x00\x00\x00IEND\xaeB`\x82"
# JPEG start-of-frame markers carry the dimensions (everything but DHT/JPG/DAC).
_SOF = {*range(0xC0, 0xC4), *range(0xC5, 0xC8), *range(0xC9, 0xCC), *range(0xCD, 0xD0)}

_DDL = """
CREATE TABLE IF NOT EXISTS assets (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  mime TEXT NOT NULL,
  filename TEXT NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  size INTEGER NOT NULL,
  data BLOB NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS assets_owner ON assets(owner_id);
"""


class AssetNotFound(Exception):
    """No such asset for this owner (also raised for another owner's asset)."""


class InvalidImage(ValueError):
    """The bytes are not an acceptable PNG/JPEG (message is safe to show the user)."""


@dataclass(frozen=True)
class ImageInfo:
    mime: str
    width: int
    height: int


def sniff_image(data: bytes) -> ImageInfo:
    """Validate ``data`` as a complete PNG or JPEG and read its size from the header."""
    if len(data) > MAX_ASSET_BYTES:
        raise InvalidImage(f"image is larger than {MAX_ASSET_BYTES // (1024 * 1024)} MB")
    if data.startswith(_PNG_SIG):
        info = _png_info(data)
    elif data.startswith(b"\xff\xd8\xff"):
        info = _jpeg_info(data)
    else:
        raise InvalidImage("only PNG and JPEG images are accepted")
    if info.width < 1 or info.height < 1:
        raise InvalidImage("image has no size")
    if info.width > MAX_SIDE_PX or info.height > MAX_SIDE_PX:
        raise InvalidImage(f"image is larger than {MAX_SIDE_PX} px on a side")
    return info


def _png_info(data: bytes) -> ImageInfo:
    # signature, then IHDR: length(4) "IHDR" width(4) height(4)
    if len(data) < 33 or data[12:16] != b"IHDR":
        raise InvalidImage("not a valid PNG")
    if not data.endswith(_PNG_IEND):
        raise InvalidImage("PNG is truncated or corrupt")
    width, height = struct.unpack(">II", data[16:24])
    return ImageInfo("image/png", width, height)


def _jpeg_info(data: bytes) -> ImageInfo:
    if not data.rstrip(b"\x00").endswith(b"\xff\xd9"):
        raise InvalidImage("JPEG is truncated or corrupt")
    i, n = 2, len(data)
    while i + 4 <= n:
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        if marker == 0xFF:  # fill byte
            i += 1
            continue
        if marker == 0xDA or marker == 0xD9:  # image data begins / ends before any SOF
            break
        (length,) = struct.unpack(">H", data[i + 2 : i + 4])
        if marker in _SOF:
            if i + 9 > n:
                break
            height, width = struct.unpack(">HH", data[i + 5 : i + 9])
            return ImageInfo("image/jpeg", width, height)
        i += 2 + length
    raise InvalidImage("not a valid JPEG")


class AssetStore(Protocol):
    def put(
        self, owner_id: str, data: bytes, mime: str, filename: str, size: tuple[int, int]
    ) -> dict: ...
    def get(self, owner_id: str, asset_id: str) -> dict: ...
    def delete(self, owner_id: str, asset_id: str) -> None: ...
    def usage(self, owner_id: str) -> int: ...
    def owned(self, owner_id: str, asset_ids: list[str]) -> set[str]: ...
    def export_all(self, owner_id: str) -> list[dict]: ...
    def erase_owner(self, owner_id: str) -> int: ...


def _now() -> str:
    return datetime.now(UTC).isoformat()


def default_path() -> Path:
    env = os.environ.get("EXAM_ASSETS_PATH")
    return Path(env) if env else Path.home() / ".exam_engine" / "assets.sqlite3"


def _asset(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "mime": row["mime"],
        "filename": row["filename"],
        "width": row["width"],
        "height": row["height"],
        "bytes": row["size"],
        "data": bytes(row["data"]),
    }


class SqliteAssetStore:
    """stdlib-sqlite3 BLOB store; one short-lived connection per call."""

    def __init__(self, path: Path):
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(_DDL)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def put(
        self, owner_id: str, data: bytes, mime: str, filename: str, size: tuple[int, int]
    ) -> dict:
        asset_id = uuid.uuid4().hex
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO assets VALUES (?,?,?,?,?,?,?,?,?)",
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
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM assets WHERE id = ? AND owner_id = ?", (asset_id, owner_id)
            ).fetchone()
        if row is None:
            raise AssetNotFound(asset_id)
        return _asset(row)

    def delete(self, owner_id: str, asset_id: str) -> None:
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "DELETE FROM assets WHERE id = ? AND owner_id = ?", (asset_id, owner_id)
            )
            if cur.rowcount == 0:
                raise AssetNotFound(asset_id)

    def usage(self, owner_id: str) -> int:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(size), 0) AS total FROM assets WHERE owner_id = ?",
                (owner_id,),
            ).fetchone()
        return int(row["total"])

    def owned(self, owner_id: str, asset_ids: list[str]) -> set[str]:
        if not asset_ids:
            return set()
        marks = ",".join("?" * len(asset_ids))
        with closing(self._connect()) as conn:
            rows = conn.execute(
                f"SELECT id FROM assets WHERE owner_id = ? AND id IN ({marks})",  # noqa: S608
                (owner_id, *asset_ids),
            ).fetchall()
        return {r["id"] for r in rows}

    def export_all(self, owner_id: str) -> list[dict]:
        """Every asset the owner has, bytes included (data export), oldest first."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM assets WHERE owner_id = ? ORDER BY created_at, id", (owner_id,)
            ).fetchall()
        return [_asset(r) for r in rows]

    def erase_owner(self, owner_id: str) -> int:
        with closing(self._connect()) as conn, conn:
            return conn.execute("DELETE FROM assets WHERE owner_id = ?", (owner_id,)).rowcount


@lru_cache(maxsize=8)
def _store_at(path: Path) -> SqliteAssetStore:
    return SqliteAssetStore(path)


def get_asset_store() -> AssetStore:
    """FastAPI dependency: the configured store (env read per call so tests can redirect it)."""
    from . import pgstores

    if url := pgstores.database_url():
        return pgstores.PgAssetStore(pgstores.get_database(url))
    return _store_at(default_path())
