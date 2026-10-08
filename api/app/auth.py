"""The identity seam (ADR-0022).

``current_owner`` is the ONLY place identity enters the API. Every document, bank, asset and
export route takes the owner id it returns, so tenancy is enforced everywhere.

Real identity (W3): a valid session cookie (set by ``/auth/<provider>/callback`` after Google /
Microsoft / GitHub sign-in) resolves to the user's id. The W1 development stub remains for
local work and tests: with ``EXAM_DEV_AUTH=1`` a request without a session is the
``X-Dev-Owner`` header (default ``local`` — the same owner the ``mathgen`` CLI uses). Without a
session *and* without that env var every request is **401**, so the stub can never silently
serve a public deployment.
"""

from __future__ import annotations

import os
import re

from fastapi import Header, HTTPException, Request

_OWNER_RE = re.compile(r"^[A-Za-z0-9_.@-]{1,64}$")

SESSION_COOKIE = "exam_session"


def current_owner(request: Request, x_dev_owner: str | None = Header(default=None)) -> str:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        from .accounts import get_account_store  # lazy: no account DB for anonymous requests

        user = get_account_store().user_for_session(token)
        if user is not None:
            return user["id"]
    if os.environ.get("EXAM_DEV_AUTH") != "1":
        raise HTTPException(status_code=401, detail="authentication required")
    owner = (x_dev_owner or "local").strip()
    if not _OWNER_RE.match(owner):
        raise HTTPException(status_code=400, detail="invalid X-Dev-Owner")
    return owner
