"""W2b — image upload and fetch (ADR-0022): owner-scoped, PNG/JPEG only.

``POST /assets`` takes the image as the raw request body (``X-Filename`` optional): no
multipart dependency, and the bytes are validated here whatever the client claims.
``GET /assets/{id}`` serves them back with a fixed content type and ``nosniff``.
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import Response

from .assets import (
    MAX_ASSET_BYTES,
    MAX_OWNER_BYTES,
    AssetNotFound,
    AssetStore,
    InvalidImage,
    get_asset_store,
    sniff_image,
)
from .auth import current_owner

router = APIRouter(prefix="/assets")

Owner = Annotated[str, Depends(current_owner)]
Store = Annotated[AssetStore, Depends(get_asset_store)]
_NAME_STRIP_RE = re.compile(r"[^A-Za-z0-9._ -]+")


def _clean_name(raw: str | None) -> str:
    name = _NAME_STRIP_RE.sub("", (raw or "").strip())[:120]
    return name or "image"


@router.post("", status_code=201)
async def upload_asset(
    request: Request,
    owner: Owner,
    store: Store,
    x_filename: Annotated[str | None, Header()] = None,
) -> dict:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_ASSET_BYTES:
        raise HTTPException(status_code=413, detail="image is larger than 2 MB")
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > MAX_ASSET_BYTES:
            raise HTTPException(status_code=413, detail="image is larger than 2 MB")
    try:
        info = sniff_image(bytes(data))
    except InvalidImage as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    if store.usage(owner) + len(data) > MAX_OWNER_BYTES:
        raise HTTPException(status_code=413, detail="image storage limit (50 MB) reached")
    return store.put(
        owner, bytes(data), info.mime, _clean_name(x_filename), (info.width, info.height)
    )


@router.get("/{asset_id}")
def get_asset(asset_id: str, owner: Owner, store: Store) -> Response:
    try:
        asset = store.get(owner, asset_id)
    except AssetNotFound:
        raise HTTPException(status_code=404, detail="asset not found") from None
    return Response(
        content=asset["data"],
        media_type=asset["mime"],
        headers={
            "X-Content-Type-Options": "nosniff",
            # ids are random and the bytes never change, so they cache for good
            "Cache-Control": "private, max-age=31536000, immutable",
        },
    )
