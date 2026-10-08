"""W2c — Convert to free-form (ADR-0021 tier 3).

The engine turns a canonical question into text blocks plus figure placeholders (pure); this
boundary rasterises each figure to a PNG with the same headless Chromium the PDFs use, stores
it as the caller's asset, and swaps the placeholder for an ``image`` node. A figure that
cannot be drawn is dropped and named in ``dropped`` — the conversion still succeeds.
"""

from __future__ import annotations

import base64
import binascii
import re
from typing import Annotated

from exam_engine import canonical, diagram
from exam_engine.canonical import CanonicalValidationError
from exam_engine.convert import to_freeform
from fastapi import APIRouter, Depends, HTTPException

from . import export
from .assets import MAX_OWNER_BYTES, AssetStore, InvalidImage, get_asset_store, sniff_image
from .auth import current_owner
from .models import ConvertFreeformRequest
from .ops import strip_ui_hints
from .quota import export_slot

router = APIRouter(prefix="/convert")

Owner = Annotated[str, Depends(current_owner)]
Assets = Annotated[AssetStore, Depends(get_asset_store)]

_DATA_URI_RE = re.compile(r"^data:image/(?:png|jpeg);base64,(?P<b64>[A-Za-z0-9+/=\s]+)$")
_FIGURE_WIDTH_PCT = 60


def _decode_raster(spec: dict) -> bytes | None:
    match = _DATA_URI_RE.match(str(spec.get("asset_ref", "")))
    if not match:
        return None
    try:
        return base64.b64decode(match.group("b64"), validate=False)
    except (binascii.Error, ValueError):
        return None


def _rasterise(specs: list[dict]) -> list[bytes | None]:
    """PNG/JPEG bytes per figure spec (``None`` where it could not be produced)."""
    results: list[bytes | None] = [None] * len(specs)
    to_draw: list[tuple[int, str]] = []
    for i, spec in enumerate(specs):
        if spec.get("type") == "raster":
            results[i] = _decode_raster(spec)
        else:
            to_draw.append((i, diagram.render_svg(spec)))
    if to_draw:
        with export_slot():
            pngs = export.html_to_png_many([svg for _, svg in to_draw])
        for (i, _), png in zip(to_draw, pngs, strict=True):
            results[i] = png
    return results


@router.post("/freeform")
def convert_freeform(req: ConvertFreeformRequest, owner: Owner, assets: Assets) -> dict:
    try:
        obj = canonical.load(strip_ui_hints(req.question))
    except CanonicalValidationError as e:
        raise HTTPException(status_code=422, detail=f"invalid question: {e}") from e

    draft = to_freeform(obj)
    placeholders = [b for b in (*draft["body"], *draft["answer"]) if b["type"] == "figure"]
    images = _rasterise([b["spec"] for b in placeholders])

    dropped: list[str] = []
    resolved: dict[int, dict] = {}
    used = assets.usage(owner)
    for block, data in zip(placeholders, images, strict=True):
        label = block["label"]
        if data is None:
            dropped.append(f"{label} (could not be drawn)")
            continue
        try:
            info = sniff_image(data)
        except InvalidImage as e:
            dropped.append(f"{label} ({e})")
            continue
        if used + len(data) > MAX_OWNER_BYTES:
            dropped.append(f"{label} (image storage limit reached)")
            continue
        used += len(data)
        meta = assets.put(owner, data, info.mime, "figure.png", (info.width, info.height))
        resolved[id(block)] = {
            "type": "image",
            "attrs": {
                "asset_id": meta["id"],
                "alt": block["alt"],
                "width_pct": _FIGURE_WIDTH_PCT,
            },
        }

    def swap(blocks: list[dict]) -> list[dict]:
        return [
            resolved[id(b)] if b["type"] == "figure" else b
            for b in blocks
            if b["type"] != "figure" or id(b) in resolved
        ]

    return {
        "marks": draft["marks"],
        "content": swap(draft["body"]),
        "answer": {"type": "doc", "content": swap(draft["answer"])},
        "dropped": dropped,
    }
