"""W3b — the bank the API reads and writes: the owner's questions, on whichever database.

With ``EXAM_DATABASE_URL`` set it is the Postgres bank; otherwise the engine's SQLite ``Bank``
(which the ``mathgen`` CLI also uses). Both expose ``search`` / ``add`` / ``get`` / ``close``.
"""

from __future__ import annotations

from typing import Protocol

from exam_engine.bank import open_bank


class BankLike(Protocol):
    def add(self, obj: dict, *, overwrite: bool = False) -> dict: ...
    def get(self, obj_id: str) -> dict: ...
    def mark_reviewed(self, obj_id: str) -> dict: ...
    def search(
        self,
        *,
        topic: str | None = None,
        difficulty: str | None = None,
        level: str | None = None,
        source_type: str | None = None,
        reviewed: bool | None = None,
    ) -> list[dict]: ...
    def close(self) -> None: ...


def open_owner_bank(owner_id: str) -> BankLike:
    from . import pgstores

    if url := pgstores.database_url():
        return pgstores.PgBank(pgstores.get_database(url), owner_id)
    return open_bank(owner_id=owner_id)
