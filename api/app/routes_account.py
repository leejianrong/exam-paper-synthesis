"""W5 — the privacy promises: export everything I have, and delete my account.

``GET /account/export`` streams a zip of the owner's data: ``account.json``, every document
(``documents/<id>.json``), every bank question (``bank/<n>-<id>.json``) and every uploaded image
as its original bytes (``assets/<id>.<ext>`` plus ``assets/index.json``). ``DELETE /account``
erases all of it — documents, images, bank rows, export events, sessions, linked sign-ins and the
user row — and needs ``{"confirm": "DELETE"}`` so a stray request can never do it.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from contextlib import closing
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from . import usage
from .accounts import AccountStore, get_account_store
from .assets import AssetStore, get_asset_store
from .auth import SESSION_COOKIE, current_owner
from .bankstore import open_owner_bank
from .docstore import DocumentStore, get_store

router = APIRouter(prefix="/account")

Owner = Annotated[str, Depends(current_owner)]
Docs = Annotated[DocumentStore, Depends(get_store)]
Assets = Annotated[AssetStore, Depends(get_asset_store)]
Accounts = Annotated[AccountStore, Depends(get_account_store)]

CONFIRM_WORD = "DELETE"
_EXT = {"image/png": "png", "image/jpeg": "jpg"}
_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


class DeleteAccountRequest(BaseModel):
    confirm: str = ""


def _put_json(zf: zipfile.ZipFile, name: str, payload: object) -> None:
    zf.writestr(name, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


@router.get("/export")
def export_account(owner: Owner, docs: Docs, assets: Assets, accounts: Accounts) -> Response:
    user = accounts.get_user(owner)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        documents = [docs.get(owner, d["id"]) for d in docs.list(owner)]
        with closing(open_owner_bank(owner)) as bank:
            questions = bank.search()
        images = assets.export_all(owner)
        _put_json(
            zf,
            "account.json",
            {
                "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "id": owner,
                "email": user["email"] if user else None,
                "name": user["name"] if user else None,
                "counts": {
                    "documents": len(documents),
                    "bank_questions": len(questions),
                    "images": len(images),
                },
            },
        )
        for rec in documents:
            _put_json(zf, f"documents/{rec['id']}.json", rec)
        for n, obj in enumerate(questions, start=1):
            _put_json(
                zf, f"bank/{n:04d}-{_SAFE_RE.sub('_', str(obj.get('id', 'q')))[:80]}.json", obj
            )
        index = []
        for img in images:
            name = f"{img['id']}.{_EXT.get(img['mime'], 'bin')}"
            zf.writestr(f"assets/{name}", img["data"])
            index.append({k: v for k, v in img.items() if k != "data"} | {"file": name})
        _put_json(zf, "assets/index.json", index)
    return Response(
        buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="exam-paper-data.zip"',
            "Cache-Control": "no-store",
        },
    )


@router.delete("", status_code=204)
def delete_account(
    body: DeleteAccountRequest,
    owner: Owner,
    docs: Docs,
    assets: Assets,
    accounts: Accounts,
) -> Response:
    if body.confirm != CONFIRM_WORD:
        raise HTTPException(status_code=422, detail=f'send {{"confirm": "{CONFIRM_WORD}"}}')
    docs.erase_owner(owner)
    assets.erase_owner(owner)
    with closing(open_owner_bank(owner)) as bank:
        bank.erase()
    usage.get_ledger().erase_owner(owner)
    accounts.delete_user(owner)  # sessions + sign-ins + the user (a no-op for dev-stub owners)
    resp = Response(status_code=204)
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp
