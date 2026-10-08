"""W3 — sign-in, sign-out and "who am I" (ADR-0022): Google, Microsoft, GitHub; no passwords.

Flow: ``GET /auth/{provider}/login`` sends the browser to the provider with a random ``state``
and a PKCE verifier, both held in short-lived HttpOnly cookies; ``GET …/callback`` checks the
state against the cookie (login CSRF), exchanges the code, resolves or creates the account,
starts a server-side session and redirects back to the web app. The session cookie is
HttpOnly + SameSite=Lax (+ Secure on https). Redirects only ever go to the configured web URL.
"""

from __future__ import annotations

import hmac
import os
from collections.abc import Iterator
from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response

from . import ratelimit, usage
from .accounts import SESSION_TTL, AccountStore, get_account_store
from .auth import SESSION_COOKIE, current_owner
from .oauth import (
    PROVIDERS,
    OAuthError,
    authorization_url,
    enabled_providers,
    fetch_profile,
    new_state,
    new_verifier,
)

router = APIRouter(prefix="/auth", dependencies=[Depends(ratelimit.limit_auth)])

Accounts = Annotated[AccountStore, Depends(get_account_store)]
_STATE_COOKIE = "exam_oauth_state"
_VERIFIER_COOKIE = "exam_oauth_verifier"
_FLOW_TTL_S = 600


def public_url() -> str:
    return os.environ.get("EXAM_PUBLIC_URL", "http://localhost:8000").rstrip("/")


def web_url() -> str:
    return os.environ.get("EXAM_WEB_URL", "http://localhost:5173").rstrip("/")


def _secure() -> bool:
    return public_url().startswith("https://")


def get_http_client() -> Iterator[httpx.Client]:
    with httpx.Client(timeout=10.0) as client:
        yield client


def _redirect_uri(provider: str) -> str:
    return f"{public_url()}/auth/{provider}/callback"


def _fail(code: str, *, retry_after: int | None = None) -> RedirectResponse:
    resp = RedirectResponse(f"{web_url()}/#/login?{urlencode({'error': code})}", status_code=302)
    if retry_after:
        resp.headers["Retry-After"] = str(retry_after)
    resp.delete_cookie(_STATE_COOKIE, path="/auth")
    resp.delete_cookie(_VERIFIER_COOKIE, path="/auth")
    return resp


@router.get("/providers")
def providers() -> dict:
    return {
        "providers": [{"name": p.name, "label": p.label} for p in enabled_providers()],
        "dev": os.environ.get("EXAM_DEV_AUTH") == "1",
    }


@router.get("/{provider}/login")
def login(provider: str, request: Request) -> RedirectResponse:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="unknown provider")
    if wait := ratelimit.sign_in_wait(request):
        return _fail("rate_limited", retry_after=wait)
    state, verifier = new_state(), new_verifier()
    try:
        url = authorization_url(
            provider, state=state, verifier=verifier, redirect_uri=_redirect_uri(provider)
        )
    except OAuthError:
        return _fail("not_configured")
    resp = RedirectResponse(url, status_code=302)
    for name, value in ((_STATE_COOKIE, state), (_VERIFIER_COOKIE, verifier)):
        resp.set_cookie(
            name,
            value,
            max_age=_FLOW_TTL_S,
            httponly=True,
            samesite="lax",
            secure=_secure(),
            path="/auth",
        )
    return resp


@router.get("/{provider}/callback")
def callback(
    provider: str,
    request: Request,
    accounts: Accounts,
    client: Annotated[httpx.Client, Depends(get_http_client)],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    exam_oauth_state: Annotated[str | None, Cookie()] = None,
    exam_oauth_verifier: Annotated[str | None, Cookie()] = None,
) -> RedirectResponse:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="unknown provider")
    if wait := ratelimit.sign_in_wait(request):
        return _fail("rate_limited", retry_after=wait)
    if error:
        return _fail("denied")
    # The state must come back exactly as this browser was given it (login CSRF).
    if (
        not code
        or not state
        or not exam_oauth_state
        or not exam_oauth_verifier
        or not hmac.compare_digest(state, exam_oauth_state)
    ):
        ratelimit.record_sign_in_failure(request)
        return _fail("state")
    try:
        profile = fetch_profile(
            provider,
            code=code,
            verifier=exam_oauth_verifier,
            redirect_uri=_redirect_uri(provider),
            client=client,
        )
    except (OAuthError, httpx.HTTPError):
        ratelimit.record_sign_in_failure(request)
        return _fail("provider")

    user = accounts.login(profile)
    token = accounts.create_session(user["id"])
    resp = RedirectResponse(f"{web_url()}/#/", status_code=302)
    resp.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=_secure(),
        path="/",
    )
    resp.delete_cookie(_STATE_COOKIE, path="/auth")
    resp.delete_cookie(_VERIFIER_COOKIE, path="/auth")
    return resp


@router.get("/me")
def me(request: Request, accounts: Accounts) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    user = accounts.user_for_session(token) if token else None
    if user is not None:
        return {"id": user["id"], "email": user["email"], "name": user["name"], "dev": False}
    if os.environ.get("EXAM_DEV_AUTH") == "1":
        owner = (request.headers.get("x-dev-owner") or "local").strip()
        return {"id": owner, "email": None, "name": "Local development", "dev": True}
    raise HTTPException(status_code=401, detail="authentication required")


@router.post("/logout", status_code=204)
def logout(request: Request, accounts: Accounts) -> Response:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        accounts.delete_session(token)
    resp = Response(status_code=204)
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


@router.get("/quota")
def quota(owner: Annotated[str, Depends(current_owner)]) -> dict:
    """The caller's export allowance, for the UI ("exports left today")."""
    limits = usage.limits_from_env()
    day, minute = usage.get_ledger().used(owner)
    return {
        "per_day": limits.per_day,
        "per_minute": limits.per_minute,
        "used_day": day,
        "used_minute": minute,
        "left_day": None if limits.per_day <= 0 else max(0, limits.per_day - day),
    }
