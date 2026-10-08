"""W1d — the owner's question bank for the editor's "From my bank" tab.

Content gets in through ``mathgen bank import`` or ``POST /bank/import`` (W2c, the editor's
import screen). Every query is scoped to the authenticated owner (ADR-0022), so sourced
and hand-authored questions never leak between teachers.
"""

from __future__ import annotations

import json
from contextlib import closing
from typing import Annotated

from exam_engine import canonical
from exam_engine.canonical import CanonicalValidationError
from exam_engine.errors import BankDuplicateId, BankObjectNotFound
from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import current_owner
from .bankstore import BankLike, open_owner_bank
from .models import BankImportRequest

router = APIRouter()

MAX_IMPORT_OBJECTS = 200
MAX_IMPORT_BYTES = 2 * 1024 * 1024

Owner = Annotated[str, Depends(current_owner)]


@router.get("/bank")
def list_bank(
    owner: Owner,
    topic: str | None = None,
    level: str | None = None,
    difficulty: str | None = None,
    source_type: str | None = None,
    reviewed: bool | None = None,
) -> dict:
    """The owner's bank questions, oldest first, optionally filtered."""
    with closing(open_owner_bank(owner)) as bank:
        objects = bank.search(
            topic=topic,
            level=level,
            difficulty=difficulty,
            source_type=source_type,
            reviewed=reviewed,
        )
    return {
        "items": [
            {
                "id": obj["id"],
                "topic": obj.get("syllabus", {}).get("topic"),
                "level": obj.get("syllabus", {}).get("level"),
                "difficulty": obj.get("cognitive", {}).get("difficulty"),
                "source_type": obj["source_type"],
                "reviewed": bool(obj.get("validation", {}).get("checks", {}).get("human_reviewed")),
                "question": obj,
            }
            for obj in objects
        ]
    }


async def _read_import(request: Request) -> BankImportRequest:
    """Parse the body ourselves so the 2 MB cap holds even without a Content-Length."""
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="import is larger than 2 MB")
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > MAX_IMPORT_BYTES:
            raise HTTPException(status_code=413, detail="import is larger than 2 MB")
    try:
        return BankImportRequest.model_validate(json.loads(bytes(data)))
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=422, detail=f"invalid import request: {e}") from None


def _unreviewed(obj: dict) -> dict:
    """Items arrive unreviewed (ADR-0019): review is a deliberate act, never inherited."""
    checks = {**obj.get("validation", {}).get("checks", {}), "human_reviewed": False}
    return {**obj, "validation": {**obj.get("validation", {}), "checks": checks}}


def _exists(bank: BankLike, obj_id: str) -> bool:
    try:
        bank.get(obj_id)
    except BankObjectNotFound:
        return False
    return True


@router.post("/bank/import")
async def import_bank(request: Request, owner: Owner) -> dict:
    """Import canonical objects into the caller's bank, review-gated, one result per item.

    One bad item never blocks the rest. A duplicate id is reported, not overwritten, unless
    ``replace`` is set. Every object passes the canonical load gate; failures carry the
    schema's path-pointed errors.
    """
    req = await _read_import(request)
    if len(req.objects) > MAX_IMPORT_OBJECTS:
        raise HTTPException(
            status_code=422, detail=f"at most {MAX_IMPORT_OBJECTS} questions per import"
        )
    results: list[dict] = []
    with closing(open_owner_bank(owner)) as bank:
        for index, raw in enumerate(req.objects):
            item: dict = {"index": index, "id": raw.get("id") if isinstance(raw, dict) else None}
            if not isinstance(raw, dict):
                results.append(
                    {**item, "status": "invalid", "errors": ["<root>: must be an object"]}
                )
                continue
            try:
                canonical.load(raw)
                existed = _exists(bank, raw["id"])
                stored = bank.add(_unreviewed(raw), overwrite=req.replace)
            except CanonicalValidationError as e:
                item |= {"status": "invalid", "errors": e.errors}
            except BankDuplicateId:
                item |= {
                    "status": "duplicate",
                    "errors": ["a question with this id is already in your bank"],
                }
            else:
                item |= {"id": stored["id"], "status": "replaced" if existed else "imported"}
            results.append(item)
    counts = {
        k: sum(1 for r in results if r["status"] == k)
        for k in ("imported", "replaced", "duplicate", "invalid")
    }
    return {"results": results, **counts}
