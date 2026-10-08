"""W3 — the OAuth 2.0 authorization-code flow for Google, Microsoft and GitHub (ADR-0022).

Deliberately small and explicit: build the authorize URL (with a random ``state`` bound to the
browser by a cookie, and PKCE S256), exchange the code over TLS, then read the profile from
the provider's userinfo endpoint with the access token we just received from the token
endpoint. Nothing here stores anything; ``routes_auth`` owns cookies and sessions.

``email_verified`` is only ever True when the provider says so: Google's ``email_verified``
claim, GitHub's *primary and verified* address. Microsoft does not assert it, so a Microsoft
email never links accounts.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from .accounts import Profile


class OAuthError(Exception):
    """The provider refused, or answered with something unusable (message is for logs)."""


@dataclass(frozen=True)
class Provider:
    name: str
    label: str
    authorize_url: str
    token_url: str
    scope: str


PROVIDERS: dict[str, Provider] = {
    "google": Provider(
        "google",
        "Google",
        "https://accounts.google.com/o/oauth2/v2/auth",
        "https://oauth2.googleapis.com/token",
        "openid email profile",
    ),
    "microsoft": Provider(
        "microsoft",
        "Microsoft",
        "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "openid email profile",
    ),
    "github": Provider(
        "github",
        "GitHub",
        "https://github.com/login/oauth/authorize",
        "https://github.com/login/oauth/access_token",
        "read:user user:email",
    ),
}

_GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"
_MICROSOFT_USERINFO = "https://graph.microsoft.com/oidc/userinfo"
_GITHUB_USER = "https://api.github.com/user"
_GITHUB_EMAILS = "https://api.github.com/user/emails"


def credentials(provider: str) -> tuple[str, str] | None:
    """``(client_id, client_secret)`` from the environment, or ``None`` if not configured."""
    key = provider.upper()
    cid, secret = (
        os.environ.get(f"EXAM_OAUTH_{key}_CLIENT_ID"),
        os.environ.get(f"EXAM_OAUTH_{key}_CLIENT_SECRET"),
    )
    return (cid, secret) if cid and secret else None


def enabled_providers() -> list[Provider]:
    return [p for name, p in PROVIDERS.items() if credentials(name)]


def new_state() -> str:
    return secrets.token_urlsafe(24)


def new_verifier() -> str:
    return secrets.token_urlsafe(48)


def challenge_for(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def authorization_url(provider: str, *, state: str, verifier: str, redirect_uri: str) -> str:
    creds = credentials(provider)
    if creds is None:
        raise OAuthError(f"{provider} sign-in is not configured")
    spec = PROVIDERS[provider]
    params = {
        "client_id": creds[0],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": spec.scope,
        "state": state,
        "code_challenge": challenge_for(verifier),
        "code_challenge_method": "S256",
    }
    if provider == "google":
        params["prompt"] = "select_account"
    return f"{spec.authorize_url}?{urlencode(params)}"


def _json(resp: httpx.Response, what: str) -> dict:
    if resp.status_code != 200:
        raise OAuthError(f"{what}: HTTP {resp.status_code}")
    try:
        data = resp.json()
    except ValueError:
        raise OAuthError(f"{what}: not JSON") from None
    if not isinstance(data, dict | list):
        raise OAuthError(f"{what}: unexpected body")
    return data  # type: ignore[return-value]


def fetch_profile(
    provider: str, *, code: str, verifier: str, redirect_uri: str, client: httpx.Client
) -> Profile:
    """Exchange ``code`` for a token and read who signed in. Raises :class:`OAuthError`."""
    creds = credentials(provider)
    if creds is None:
        raise OAuthError(f"{provider} sign-in is not configured")
    spec = PROVIDERS[provider]
    token_resp = client.post(
        spec.token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": creds[0],
            "client_secret": creds[1],
            "code_verifier": verifier,
        },
        headers={"Accept": "application/json"},
    )
    token = _json(token_resp, "token exchange")
    access = token.get("access_token") if isinstance(token, dict) else None
    if not isinstance(access, str) or not access or token.get("error"):
        raise OAuthError("token exchange: no access token")
    auth = {"Authorization": f"Bearer {access}", "Accept": "application/json"}

    if provider == "github":
        user = _json(client.get(_GITHUB_USER, headers=auth), "github user")
        assert isinstance(user, dict)
        if user.get("id") is None:
            raise OAuthError("github user: no id")
        email = None
        emails = _json(client.get(_GITHUB_EMAILS, headers=auth), "github emails")
        if isinstance(emails, list):
            primary = next(
                (
                    e
                    for e in emails
                    if isinstance(e, dict) and e.get("primary") and e.get("verified")
                ),
                None,
            )
            email = primary["email"] if primary else None
        return Profile(
            "github",
            str(user["id"]),
            email,
            email is not None,
            user.get("name") or user.get("login"),
        )

    url = _GOOGLE_USERINFO if provider == "google" else _MICROSOFT_USERINFO
    info = _json(client.get(url, headers=auth), f"{provider} userinfo")
    assert isinstance(info, dict)
    subject = info.get("sub")
    if not isinstance(subject, str) or not subject:
        raise OAuthError(f"{provider} userinfo: no subject")
    email = info.get("email") if isinstance(info.get("email"), str) else None
    verified = provider == "google" and info.get("email_verified") is True
    return Profile(provider, subject, email, bool(email and verified), info.get("name"))
