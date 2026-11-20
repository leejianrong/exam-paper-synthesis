"""W1d — the owner's question bank for the editor's "From my bank" tab.

Content gets in through ``mathgen bank import`` or ``POST /bank/import`` (W2c, the editor's
import screen). Every query is scoped to the authenticated owner (ADR-0022), so sourced
and hand-authored questions never leak between teachers.
"""

from __future__ import annotations

import json
from contextlib import closing
from typing import Annotated

from exam_engine import canonical, own_question
from exam_engine.canonical import CanonicalValidationError
from exam_engine.document import referenced_assets
from exam_engine.errors import BankDuplicateId, BankObjectNotFound
from fastapi import APIRouter, Depends, HTTPException, Request

from .assets import AssetStore, get_asset_store
from .auth import current_owner
from .bankstore import BankLike, open_owner_bank
from .models import BankImportRequest, BankReviewRequest, BankSaveOwnRequest

router = APIRouter()

MAX_IMPORT_OBJECTS = 200
MAX_IMPORT_BYTES = 2 * 1024 * 1024

Owner = Annotated[str, Depends(current_owner)]
Assets = Annotated[AssetStore, Depends(get_asset_store)]


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
    return {"items": [bank_item(obj) for obj in objects]}


def bank_item(obj: dict) -> dict:
    """One bank question as the API lists it (also the bank swap's picker, EXA-33)."""
    return {
        "id": obj["id"],
        "topic": obj.get("syllabus", {}).get("topic"),
        "level": obj.get("syllabus", {}).get("level"),
        "difficulty": obj.get("cognitive", {}).get("difficulty"),
        "source_type": obj["source_type"],
        "reviewed": bool(obj.get("validation", {}).get("checks", {}).get("human_reviewed")),
        "question": obj,
    }


@router.put("/bank/{obj_id:path}/review")
def review_bank_item(obj_id: str, req: BankReviewRequest, owner: Owner) -> dict:
    """Mark one of the caller's imported questions reviewed, or withdraw that (ADR-0019).

    Review is a deliberate human act: nothing else ever sets it (imports arrive unreviewed, and
    ``replace`` resets it). Only ``sourced`` questions go through the gate; generated ones are
    proven by construction. Owner-scoped: someone else's id is a 404.
    """
    with closing(open_owner_bank(owner)) as bank:
        try:
            current = bank.get(obj_id)
        except BankObjectNotFound:
            raise HTTPException(status_code=404, detail="no such question in your bank") from None
        if current.get("source_type") != "sourced":
            raise HTTPException(
                status_code=422,
                detail="only imported (sourced) questions are reviewed; generated ones are "
                "proven by the engine",
            )
        stored = bank.set_reviewed(obj_id, req.reviewed)
    return {"id": stored["id"], "reviewed": req.reviewed}


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


def _missing_images(obj: dict, owner: str, assets: AssetStore) -> list[str]:
    """A teacher's question must only show the caller's own images (a foreign id looks
    missing), so it still draws in any of their papers."""
    if not obj.get("freeform"):
        return []
    wanted = referenced_assets({"content": {"content": [obj["freeform"]]}})
    owned = assets.owned(owner, wanted)
    return [f"freeform: image asset {a!r} does not exist" for a in wanted if a not in owned]


def _exists(bank: BankLike, obj_id: str) -> bool:
    try:
        bank.get(obj_id)
    except BankObjectNotFound:
        return False
    return True


@router.post("/bank/import")
async def import_bank(request: Request, owner: Owner, assets: Assets) -> dict:
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
                if missing := _missing_images(raw, owner, assets):
                    raise CanonicalValidationError(missing)
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


@router.get("/bank/topics")
def bank_topics(owner: Owner) -> dict:
    """The topics a teacher can file their own question under (EXA-90), with their strands."""
    return {"topics": list(own_question.topics())}


@router.post("/bank/own")
def save_own_question(req: BankSaveOwnRequest, owner: Owner, assets: Assets) -> dict:
    """Save one of the caller's own questions (a ``freeformQuestion`` block) to their bank.

    It arrives unreviewed like any import (ADR-0019) and stays unverified. Saving the same
    block again is a 409 "already in your bank" unless ``replace`` is set, which updates it.
    """
    try:
        obj = own_question.to_canonical(
            req.block, topic=req.topic, level=req.level, difficulty=req.difficulty, marks=req.marks
        )
    except own_question.NotSavable as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    except CanonicalValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors) from None
    if missing := _missing_images(obj, owner, assets):
        raise HTTPException(status_code=422, detail=missing)
    with closing(open_owner_bank(owner)) as bank:
        existed = _exists(bank, obj["id"])
        try:
            stored = bank.add(obj, overwrite=req.replace)
        except BankDuplicateId:
            raise HTTPException(
                status_code=409, detail="This question is already in your bank."
            ) from None
    return {"id": stored["id"], "status": "replaced" if existed else "saved", **bank_item(stored)}
