"""O2 — folders to organise papers (``docs/planning/editor/ORGANIZE-SHAPING.md``).

Folders live in the document store, owner-scoped like documents: another owner's folder is a
404, never a 403. Deleting a folder unfiles its papers; it never deletes them. Papers are moved
with ``PATCH /documents/{id}``.

EXA-168: a folder that holds a complete exam set (one Booklet A, one Booklet B, one Paper 2, by
the server-derived ``paper_part``; a cover's paper line beats a title, ``document.exam_set_order``)
prints one answer key for the set: ``GET /folders/{id}/key/preview`` (HTML) and ``POST
/folders/{id}/key`` (PDF, spends one export).
"""

from __future__ import annotations

from typing import Annotated
from urllib.parse import quote

from exam_engine import document as docs
from exam_engine.errors import ExamSetError
from exam_engine.render import render_set_key_html
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response

from . import export
from .assets import AssetStore, get_asset_store
from .auth import current_owner
from .docstore import (
    DocumentNotFound,
    DocumentStore,
    FolderNotFound,
    InvalidFolderName,
    get_store,
)
from .models import FolderRequest
from .quota import check_export_quota, export_slot, refund_export
from .routes_documents import _resolver, _slug

router = APIRouter(prefix="/folders")

Owner = Annotated[str, Depends(current_owner)]
Store = Annotated[DocumentStore, Depends(get_store)]
Assets = Annotated[AssetStore, Depends(get_asset_store)]


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="folder not found")


def _bad_name(e: InvalidFolderName) -> HTTPException:
    return HTTPException(status_code=422, detail=str(e))


@router.get("")
def list_folders(owner: Owner, store: Store) -> dict:
    return {"folders": store.list_folders(owner)}


@router.post("", status_code=201)
def create_folder(req: FolderRequest, owner: Owner, store: Store) -> dict:
    try:
        return store.create_folder(owner, req.name)
    except InvalidFolderName as e:
        raise _bad_name(e) from None


@router.patch("/{folder_id}")
def rename_folder(folder_id: str, req: FolderRequest, owner: Owner, store: Store) -> dict:
    try:
        return store.rename_folder(owner, folder_id, req.name)
    except InvalidFolderName as e:
        raise _bad_name(e) from None
    except FolderNotFound:
        raise _not_found() from None


@router.delete("/{folder_id}", status_code=204)
def delete_folder(folder_id: str, owner: Owner, store: Store) -> Response:
    try:
        store.delete_folder(owner, folder_id)
    except FolderNotFound:
        raise _not_found() from None
    return Response(status_code=204)


def _numbers(ns: list[int]) -> str:
    listed = ", ".join(map(str, ns[:-1])) + f" and {ns[-1]}" if len(ns) > 1 else str(ns[0])
    return f"question{'s' if len(ns) > 1 else ''} {listed}"


def _set_paper(store: DocumentStore, owner: str, folder_id: str, doc_id: str, part: str) -> dict:
    """One paper of the set, read again: deleted, moved out or changed into another part since
    the folder was listed, the set is not complete after all."""
    try:
        rec = store.get(owner, doc_id)
    except DocumentNotFound:
        rec = None
    if rec is None or rec.get("folder_id") != folder_id or rec.get("paper_part") != part:
        raise ExamSetError(
            "incomplete_set",
            f"{docs.SET_PART_NAMES[part]} was just deleted, moved or changed. "
            "Try again in a moment.",
            [part],
        )
    return rec


def _set_key_html(
    store: DocumentStore,
    assets: AssetStore,
    owner: str,
    folder_id: str,
    allow_placeholders: bool,
) -> tuple[str, str]:
    """The folder's exam set as one key: (folder name, HTML). The set is chosen from the
    folder's papers by ``document.exam_set_order`` (a cover's paper line beats a title; papers
    that name no part are not in it). 409 when the set is incomplete, ambiguous or its covers
    disagree (``mixed_set``), or (unless ``allow_placeholders``) still has empty generator
    placeholders; 422 when a paper has no questions."""
    folder = next((f for f in store.list_folders(owner) if f["id"] == folder_id), None)
    if folder is None:
        raise _not_found()
    papers = [d for d in store.list(owner) if d.get("folder_id") == folder_id]
    try:
        order = docs.exam_set_order(
            [(d.get("paper_part"), d.get("paper_part_source"), d["title"]) for d in papers]
        )
        records = [
            _set_paper(store, owner, folder_id, papers[i]["id"], part)
            for i, part in zip(order, docs.SET_PARTS, strict=True)
        ]
        docs.check_exam_set_covers([rec["document"] for rec in records])
    except ExamSetError as e:
        raise HTTPException(
            status_code=409, detail={"code": e.code, "message": e.message, "parts": e.parts}
        ) from None
    empty: list[str] = []
    pending: list[dict] = []
    said: list[str] = []
    for part, rec in zip(docs.SET_PARTS, records, strict=True):
        name = docs.SET_PART_NAMES[part]
        if not docs.numbered_blocks(rec["document"]):
            empty.append(name)
        if numbers := docs.unfilled_placeholder_numbers(rec["document"]):
            pending.append({"id": rec["id"], "part": part, "questions": numbers})
            said.append(f"{name} {_numbers(numbers)}")
    if empty:
        raise HTTPException(
            status_code=422,
            detail=f"{' and '.join(empty)} {'has' if len(empty) == 1 else 'have'} no questions "
            "to put in an answer key.",
        )
    if pending and not allow_placeholders:
        many = len(pending) > 1 or len(pending[0]["questions"]) > 1
        raise HTTPException(
            status_code=409,
            detail={
                "code": "unfilled_placeholders",
                "message": (
                    f"{'; '.join(said)} "
                    f"{'are' if many else 'is'} still empty. Write or fill "
                    f"{'them' if many else 'it'} first, or download the key anyway."
                ),
                "papers": pending,
            },
        )
    html = render_set_key_html(
        folder["name"],
        [(rec["title"], rec["document"]) for rec in records],
        assets=_resolver(assets, owner),
    )
    return folder["name"], html


def _attachment(folder_name: str) -> str:
    """An ASCII file name for old clients, then the folder's own name (RFC 6266, RFC 5987)."""
    own = quote(f"{folder_name} answer key.pdf", safe="")
    return f"attachment; filename=\"{_slug(folder_name)}-answer-key.pdf\"; filename*=UTF-8''{own}"


@router.get("/{folder_id}/key/preview")
def preview_set_key(
    folder_id: str, owner: Owner, store: Store, assets: Assets, allow_placeholders: bool = True
) -> HTMLResponse:
    """The exam set's answer key as print HTML (the PDF is made from the same markup)."""
    _, html = _set_key_html(store, assets, owner, folder_id, allow_placeholders)
    return HTMLResponse(content=html)


@router.post("/{folder_id}/key")
def export_set_key(
    folder_id: str, owner: Owner, store: Store, assets: Assets, allow_placeholders: bool = False
) -> Response:
    """The exam set's answer key as one PDF (EXA-168). Refusals (an incomplete set, empty
    placeholders) come before any export allowance is spent; a failed render is refunded."""
    name, html = _set_key_html(store, assets, owner, folder_id, allow_placeholders)
    ticket = check_export_quota(owner)
    try:
        with export_slot():
            pdf = export.html_to_pdf(html)
    except BaseException:
        refund_export(ticket)
        raise
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": _attachment(name)},
    )
