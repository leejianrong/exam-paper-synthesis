"""W1b — documents: tenant-scoped CRUD, true-print preview, and PDF export (ADR-0021/0022).

The engine owns the document model, validation, and rendering (pure); this boundary
authenticates (``current_owner``), stores (``DocumentStore``), and runs the one impure
step, headless Chromium. A foreign document is a 404, never a 403.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from exam_engine import document as docs
from exam_engine.render import render_document_html
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from . import export
from .auth import current_owner
from .docstore import DocumentNotFound, DocumentStore, VersionConflict, get_store
from .models import CreateDocumentRequest, SaveDocumentRequest
from .ops import strip_document_hints, with_document_hints
from .quota import check_export_quota, export_slot

router = APIRouter(prefix="/documents")

Owner = Annotated[str, Depends(current_owner)]
Store = Annotated[DocumentStore, Depends(get_store)]
Mode = Literal["student", "key", "full"]
# A little above the engine's content limit, to cover the JSON envelope.
_MAX_BODY_BYTES = docs.MAX_CONTENT_BYTES + 100_000
_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")
_MODE_SUFFIX = {"student": "student", "key": "answer-key", "full": "full"}


def _slug(title: str) -> str:
    return _SLUG_STRIP_RE.sub("-", title.lower()).strip("-") or "paper"


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="document not found")


def _valid_or_422(document: object) -> dict:
    errors = docs.validate_document(document)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    assert isinstance(document, dict)
    return document


@router.post("", status_code=201)
def create_document(
    req: CreateDocumentRequest,
    owner: Owner,
    store: Store,
) -> dict:
    document = docs.empty_document(req.title or "Untitled paper")
    return store.create(owner, _valid_or_422(document), 0)


@router.get("")
def list_documents(owner: Owner, store: Store) -> dict:
    return {"documents": store.list(owner)}


@router.get("/{doc_id}")
def get_document(doc_id: str, owner: Owner, store: Store) -> dict:
    try:
        return with_document_hints(store.get(owner, doc_id))
    except DocumentNotFound:
        raise _not_found() from None


@router.put("/{doc_id}")
def save_document(
    doc_id: str,
    req: SaveDocumentRequest,
    request: Request,
    owner: Owner,
    store: Store,
) -> dict:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > _MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="document is too large")
    document = _valid_or_422(strip_document_hints(req.document))
    try:
        saved = store.save(owner, doc_id, document, docs.total_marks(document), req.base_version)
        return with_document_hints(saved)
    except DocumentNotFound:
        raise _not_found() from None
    except VersionConflict as e:
        raise HTTPException(
            status_code=409,
            detail={"message": "document changed elsewhere", "current_version": e.current},
        ) from None


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: str, owner: Owner, store: Store) -> Response:
    try:
        store.delete(owner, doc_id)
    except DocumentNotFound:
        raise _not_found() from None
    return Response(status_code=204)


def _html_for(store: DocumentStore, owner: str, doc_id: str, mode: Mode) -> tuple[str, str]:
    try:
        rec = store.get(owner, doc_id)
    except DocumentNotFound:
        raise _not_found() from None
    document = rec["document"]
    if mode == "key" and not docs.numbered_blocks(document):
        raise HTTPException(status_code=422, detail="no questions to put in an answer key")
    return rec["title"], render_document_html(rec["title"], document, mode=mode)


@router.get("/{doc_id}/preview/{mode}")
def preview_document(
    doc_id: str,
    mode: Mode,
    owner: Owner,
    store: Store,
) -> HTMLResponse:
    _, html = _html_for(store, owner, doc_id, mode)
    return HTMLResponse(content=html)


@router.post("/{doc_id}/export/{mode}")
def export_document(
    doc_id: str,
    mode: Mode,
    owner: Owner,
    store: Store,
) -> Response:
    title, html = _html_for(store, owner, doc_id, mode)
    check_export_quota(owner)
    with export_slot():
        pdf = export.html_to_pdf(html)
    filename = f"{_slug(title)}-{_MODE_SUFFIX[mode]}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
