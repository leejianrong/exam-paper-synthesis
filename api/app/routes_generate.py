"""A9 — POST /generate. Batch-generates canonical objects via the engine,
stamps created_at at this boundary (ADR-0016), and dedups within the request."""

from __future__ import annotations

import random
from datetime import datetime, timezone

from exam_engine.errors import InfeasibleConstraints, UnknownBlueprint
from exam_engine.pipeline import generate, param_hash
from fastapi import APIRouter, HTTPException

from .models import GenerateRequest, GenerateResponse

router = APIRouter()

_SEED_CEIL = 2**31


@router.post("/generate", response_model=GenerateResponse)
def post_generate(req: GenerateRequest) -> GenerateResponse:
    # The API boundary is the only place entropy enters (engine stays pure).
    seed = req.seed if req.seed is not None else random.randrange(1, _SEED_CEIL)

    questions: list[dict] = []
    seen_ids: set[str] = set()
    seen_params: set[str] = set()
    # Generous attempt cap so in-session dedup can't hang the request (R4.8).
    max_tries = req.count * 50

    for _ in range(max_tries):
        if len(questions) >= req.count:
            break
        try:
            obj = generate(req.blueprint_code, seed)
        except UnknownBlueprint as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except InfeasibleConstraints as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        seed += 1

        phash = param_hash(obj)
        if obj["id"] in seen_ids or phash in seen_params:
            continue
        seen_ids.add(obj["id"])
        seen_params.add(phash)

        obj["provenance"]["created_at"] = datetime.now(timezone.utc).isoformat()
        questions.append(obj)

    if len(questions) < req.count:
        raise HTTPException(
            status_code=422,
            detail=f"could only generate {len(questions)}/{req.count} unique questions",
        )

    return GenerateResponse(questions=questions)
