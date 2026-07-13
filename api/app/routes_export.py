"""V5 — POST /export/{preview|worksheet|answer-key} (ADR-0008/0010).

Export is a read-only *view* of already-built canonical objects: the client
worksheet store POSTs its approved ``{title, questions}`` set (the engine/API
hold no session, ADR-0001). Each route validates every question through the same
canonical load gate used by ``/edit/{op}`` — a tampered/invalid object, or an
empty set, is rejected with **422**. Nothing is stamped (no ``created_at``).

The engine renderers (pure) build the HTML; ``export.html_to_pdf`` (the only
impure, browser-touching code) makes the PDF. The route just marshals, guards,
and sets headers.
"""

from __future__ import annotations

import re

from exam_engine import canonical
from exam_engine.canonical import CanonicalValidationError
from exam_engine.render import render_answer_key_html, render_worksheet_html
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

from . import export
from .models import ExportRequest

router = APIRouter(prefix="/export")

_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


def _slug(title: str) -> str:
    """Filesystem-safe slug of the title; defaults to ``worksheet`` when empty."""
    slug = _SLUG_STRIP_RE.sub("-", title.lower()).strip("-")
    return slug or "worksheet"


def _validated_questions(req: ExportRequest) -> list[dict]:
    """Load-gate every question (reject tampered/invalid); reject an empty set."""
    if not req.questions:
        raise HTTPException(status_code=422, detail="no questions to export")
    try:
        return [canonical.load(q) for q in req.questions]
    except CanonicalValidationError as e:
        raise HTTPException(status_code=422, detail=f"invalid question: {e}") from e


@router.post("/preview")
def post_preview(req: ExportRequest) -> HTMLResponse:
    questions = _validated_questions(req)
    html = render_worksheet_html(req.title, questions)
    return HTMLResponse(content=html)


@router.post("/worksheet")
def post_worksheet(req: ExportRequest) -> Response:
    questions = _validated_questions(req)
    html = render_worksheet_html(req.title, questions)
    pdf = export.html_to_pdf(html)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_slug(req.title)}.pdf"'},
    )


@router.post("/answer-key")
def post_answer_key(req: ExportRequest) -> Response:
    questions = _validated_questions(req)
    html = render_answer_key_html(req.title, questions)
    pdf = export.html_to_pdf(html)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_slug(req.title)}-answers.pdf"'},
    )
