"""O1 — ``GET /settings`` and ``PUT /settings`` for the signed-in teacher (EXA-125).

``GET`` returns every setting (stored values over the defaults). ``PUT`` takes a partial object
of known settings and returns the result; an unknown key or a wrong type is a 422.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from .auth import current_owner
from .settings import SettingsStore, UnknownSetting, get_settings_store

router = APIRouter()

Owner = Annotated[str, Depends(current_owner)]
Store = Annotated[SettingsStore, Depends(get_settings_store)]


@router.get("/settings")
def read_settings(owner: Owner, store: Store) -> dict:
    return store.get(owner)


@router.put("/settings")
def update_settings(patch: dict, owner: Owner, store: Store) -> dict:
    try:
        return store.update(owner, patch)
    except UnknownSetting as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
