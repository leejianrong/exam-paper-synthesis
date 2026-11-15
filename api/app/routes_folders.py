"""O2 — folders to organise papers (``docs/planning/editor/ORGANIZE-SHAPING.md``).

Folders live in the document store, owner-scoped like documents: another owner's folder is a
404, never a 403. Deleting a folder unfiles its papers; it never deletes them. Papers are moved
with ``PATCH /documents/{id}``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from .auth import current_owner
from .docstore import DocumentStore, FolderNotFound, InvalidFolderName, get_store
from .models import FolderRequest

router = APIRouter(prefix="/folders")

Owner = Annotated[str, Depends(current_owner)]
Store = Annotated[DocumentStore, Depends(get_store)]


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
