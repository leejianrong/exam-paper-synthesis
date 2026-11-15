"""W1b — documents: tenant-scoped CRUD, true-print preview, and PDF export (ADR-0021/0022).

The engine owns the document model, validation, and rendering (pure); this boundary
authenticates (``current_owner``), stores (``DocumentStore``), and runs the one impure
step, headless Chromium. A foreign document is a 404, never a 403.
"""

from __future__ import annotations

import random
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Literal

from exam_engine import document as docs
from exam_engine import paper, paper_swap
from exam_engine.render import render_document_html
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from . import export
from .assets import AssetNotFound, AssetStore, get_asset_store
from .auth import current_owner
from .docstore import DocumentNotFound, DocumentStore, VersionConflict, get_store
from .models import (
    CreateDocumentRequest,
    GeneratePaperRequest,
    RegeneratePaperRequest,
    SaveDocumentRequest,
    SwapQuestionRequest,
)
from .ops import strip_document_hints, with_document_hints
from .quota import check_export_quota, export_slot, refund_export

router = APIRouter(prefix="/documents")

Owner = Annotated[str, Depends(current_owner)]
Store = Annotated[DocumentStore, Depends(get_store)]
Assets = Annotated[AssetStore, Depends(get_asset_store)]
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


def _owned_assets_or_422(document: dict, owner: str, assets: AssetStore) -> None:
    """Every image must point at an asset the caller owns (a foreign id looks missing)."""
    wanted = docs.referenced_assets(document)
    missing = [a for a in wanted if a not in assets.owned(owner, wanted)]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=[f"content: image asset {a!r} does not exist" for a in missing],
        )


def _resolver(assets: AssetStore, owner: str):
    def resolve(asset_id: str) -> tuple[str, bytes] | None:
        try:
            a = assets.get(owner, asset_id)
        except AssetNotFound:
            return None
        return a["mime"], a["data"]

    return resolve


@router.post("", status_code=201)
def create_document(
    req: CreateDocumentRequest,
    owner: Owner,
    store: Store,
) -> dict:
    if req.template:
        try:
            document = paper.template_document(req.template)
        except paper.UnknownPaperTemplate:
            raise HTTPException(status_code=404, detail="unknown paper template") from None
        if req.title:
            document["title"] = req.title
    else:
        document = docs.empty_document(req.title or "Untitled paper")
    return store.create(owner, _valid_or_422(document), 0)


_SEED_CEIL = 2**31


@router.post("/generate", status_code=201)
def generate_paper(req: GeneratePaperRequest, owner: Owner, store: Store) -> dict:
    """P8a: one click, one paper. Fills the template's slots from the blueprints (the engine
    is pure; the seed — the only entropy — is chosen here, as for POST /generate) and stores
    it as a new document. The response is the document record plus the fill ``report``."""
    seed = req.seed if req.seed is not None else random.randrange(1, _SEED_CEIL)
    try:
        document, report = paper.generate_paper(req.template, req.level, seed)
    except paper.UnknownPaperTemplate:
        raise HTTPException(status_code=404, detail="unknown paper template") from None
    stamp = datetime.now(UTC).isoformat()
    for node in document["content"]["content"]:
        if node["type"] == "templatedQuestion":
            node["attrs"]["question"]["provenance"]["created_at"] = stamp
    record = store.create(owner, _valid_or_422(document), docs.total_marks(document))
    return {**with_document_hints(record), "report": report}


def _conflict(current: int) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={"message": "document changed elsewhere", "current_version": current},
    )


def _rework(
    owner: str,
    doc_id: str,
    store: DocumentStore,
    base_version: int,
    change: Callable[[dict], tuple[dict, dict]],
) -> dict:
    """P8d: apply a pure engine change to the stored paper and save it, with the same
    optimistic concurrency as PUT (the change is computed on ``base_version`` only). New
    snapshots get ``created_at`` here; the result is re-validated before it is stored."""
    try:
        rec = store.get(owner, doc_id)
    except DocumentNotFound:
        raise _not_found() from None
    if rec["version"] != base_version:
        raise _conflict(rec["version"])
    document, report = change(rec["document"])
    stamp = datetime.now(UTC).isoformat()
    for node in document["content"]["content"]:
        if node["type"] == "templatedQuestion":
            prov = node["attrs"]["question"]["provenance"]
            if not prov.get("created_at"):
                prov["created_at"] = stamp
    document = _valid_or_422(document)
    try:
        saved = store.save(owner, doc_id, document, docs.total_marks(document), base_version)
    except DocumentNotFound:
        raise _not_found() from None
    except VersionConflict as e:
        raise _conflict(e.current) from None
    return {**with_document_hints(saved), "report": report}


@router.post("/{doc_id}/swap")
def swap_question(doc_id: str, req: SwapQuestionRequest, owner: Owner, store: Store) -> dict:
    """P8d: another question like this one, one from another topic, or a placeholder to
    write, keeping the slot's marks and the paper's rules (engine ``paper_swap``)."""
    seed = req.seed if req.seed is not None else random.randrange(1, _SEED_CEIL)

    def change(document: dict) -> tuple[dict, dict]:
        try:
            return paper_swap.swap_question(document, req.block_id, req.mode, seed, req.level)
        except paper_swap.BlockNotFound:
            raise HTTPException(status_code=404, detail="question not found") from None
        except paper_swap.SwapNotPossible as e:
            raise HTTPException(status_code=422, detail=str(e)) from None

    return _rework(owner, doc_id, store, req.base_version, change)


@router.post("/{doc_id}/regenerate")
def regenerate_paper(doc_id: str, req: RegeneratePaperRequest, owner: Owner, store: Store) -> dict:
    """P8d: refill every unlocked generated question and empty placeholder; locked
    questions and the teacher's own work stay exactly as they are."""
    seed = req.seed if req.seed is not None else random.randrange(1, _SEED_CEIL)
    return _rework(
        owner,
        doc_id,
        store,
        req.base_version,
        lambda document: paper_swap.regenerate_unlocked(document, req.level, seed),
    )


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
    assets: Assets,
) -> dict:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > _MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="document is too large")
    document = _valid_or_422(strip_document_hints(req.document))
    _owned_assets_or_422(document, owner, assets)
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


def _html_for(
    store: DocumentStore, assets: AssetStore, owner: str, doc_id: str, mode: Mode
) -> tuple[str, str]:
    try:
        rec = store.get(owner, doc_id)
    except DocumentNotFound:
        raise _not_found() from None
    document = rec["document"]
    if mode == "key" and not docs.numbered_blocks(document):
        raise HTTPException(status_code=422, detail="no questions to put in an answer key")
    return rec["title"], render_document_html(
        rec["title"], document, mode=mode, assets=_resolver(assets, owner)
    )


@router.get("/{doc_id}/preview/{mode}")
def preview_document(
    doc_id: str,
    mode: Mode,
    owner: Owner,
    store: Store,
    assets: Assets,
) -> HTMLResponse:
    _, html = _html_for(store, assets, owner, doc_id, mode)
    return HTMLResponse(content=html)


@router.post("/{doc_id}/export/{mode}")
def export_document(
    doc_id: str,
    mode: Mode,
    owner: Owner,
    store: Store,
    assets: Assets,
) -> Response:
    title, html = _html_for(store, assets, owner, doc_id, mode)
    ticket = check_export_quota(owner)
    try:
        with export_slot():
            pdf = export.html_to_pdf(html)
    except BaseException:
        refund_export(ticket)  # a failed render must not cost the teacher an export
        raise
    filename = f"{_slug(title)}-{_MODE_SUFFIX[mode]}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
