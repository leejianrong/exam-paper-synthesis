"""W1d — render one question to an embeddable HTML fragment, plus the shared assets.

The editor shows bank questions (MCQs, tables, grids, constructions…) by embedding the
engine's own print markup rather than a TypeScript re-implementation, so the on-screen block
and the PDF cannot drift. Stateless, like ``/generate`` and ``/edit``.
"""

from __future__ import annotations

from typing import Literal

from exam_engine import canonical
from exam_engine.canonical import CanonicalValidationError
from exam_engine.render import fragment_css, fragment_js, render_question_fragment
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from .models import RenderQuestionRequest
from .ops import strip_ui_hints

router = APIRouter(prefix="/render")

# Assets only change with an engine release; a day is plenty for a dev/SaaS first cut.
_CACHE = {"Cache-Control": "public, max-age=86400"}


@router.post("/question")
def render_question(req: RenderQuestionRequest) -> dict:
    try:
        question = canonical.load(strip_ui_hints(req.question))
    except CanonicalValidationError as e:
        raise HTTPException(status_code=422, detail=f"invalid question: {e}") from e
    mode: Literal["student", "key"] = req.mode
    return {"html": render_question_fragment(question, mode=mode, number=req.number)}


@router.get("/question.css")
def question_css() -> Response:
    return Response(content=fragment_css(), media_type="text/css", headers=_CACHE)


@router.get("/katex.js")
def katex_js() -> Response:
    return Response(content=fragment_js(), media_type="text/javascript", headers=_CACHE)
