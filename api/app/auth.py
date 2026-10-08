"""W1b — the identity seam (ADR-0022).

``current_owner`` is the ONLY place identity enters the API. Every document route and
every store call takes the owner id it returns, so tenancy is enforced from day one.

W1 ships a development stub: with ``EXAM_DEV_AUTH=1`` the owner is the ``X-Dev-Owner`` header
(default ``local`` — the same owner the ``mathgen`` CLI and a pre-owner bank use, so what you
import on the command line shows up in the editor). Without the env var every request is
**401**, so the stub can never silently serve a public deployment. W3 replaces the body with
session-cookie → user id (Google / Microsoft / GitHub sign-in); nothing else changes.
"""

from __future__ import annotations

import os
import re

from fastapi import Header, HTTPException

_OWNER_RE = re.compile(r"^[A-Za-z0-9_.@-]{1,64}$")


def current_owner(x_dev_owner: str | None = Header(default=None)) -> str:
    if os.environ.get("EXAM_DEV_AUTH") != "1":
        raise HTTPException(status_code=401, detail="authentication required")
    owner = (x_dev_owner or "local").strip()
    if not _OWNER_RE.match(owner):
        raise HTTPException(status_code=400, detail="invalid X-Dev-Owner")
    return owner
