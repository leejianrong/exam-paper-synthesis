"""V3 — POST /edit/{op}. Applies one edit-operation transform (ADR-0004/0009).

The engine does the object->object transform (pure/deterministic); this boundary
supplies entropy (a random seed when none is given) and stamps ``created_at`` —
the only clock boundary, mirroring routes_generate.py (ADR-0016)."""

from __future__ import annotations

import random
from datetime import UTC, datetime

from exam_engine import canonical, edits
from exam_engine.canonical import CanonicalValidationError
from exam_engine.errors import EditNotApplicable, InfeasibleConstraints, UnknownBlueprint
from fastapi import APIRouter, HTTPException

from .models import EditRequest, EditResponse
from .ops import strip_ui_hints, with_available_ops

router = APIRouter()

_SEED_CEIL = 2**31


@router.post("/edit/{op}", response_model=EditResponse)
def post_edit(op: str, req: EditRequest) -> EditResponse:
    if op not in edits.KNOWN_OPS:
        raise HTTPException(status_code=404, detail=f"unknown edit op: {op!r}")

    # Validate the source on entry — reject tampered/invalid objects (R6.1).
    # Strip the UI-only available_ops hint first so the round-tripped object
    # passes the strict schema gate (KAN-243).
    try:
        source = canonical.load(strip_ui_hints(req.question))
    except CanonicalValidationError as e:
        raise HTTPException(status_code=422, detail=f"invalid question: {e}") from e

    # Supply entropy here so the engine stays pure (resample ops honour a seed).
    seed = req.seed if req.seed is not None else random.randrange(1, _SEED_CEIL)

    try:
        child = edits.apply(op, source, seed=seed)
    except EditNotApplicable as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except UnknownBlueprint as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InfeasibleConstraints as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # The only clock boundary (ADR-0016), mirroring routes_generate.
    child["provenance"]["created_at"] = datetime.now(UTC).isoformat()

    return EditResponse(question=with_available_ops(child))
