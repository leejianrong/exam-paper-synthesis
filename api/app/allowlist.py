"""EXA-186: invite-only sign-in for a closed trial.

``EXAM_ALLOWED_EMAILS`` is an optional comma-separated list of email addresses and ``@domain``
entries (``ann@school.edu.sg, @example.org``). When it is set, only a person whose sign-in
provider vouches for (verifies) an email on the list may sign in, create an account, or keep
using a session; everyone else is refused before any account is made. Unset or blank, sign-in is
open to everyone, which is how the public launch runs.
"""

import os


def _entries() -> list[str]:
    raw = os.environ.get("EXAM_ALLOWED_EMAILS", "")
    return [e.strip().lower() for e in raw.split(",") if e.strip()]


def is_invite_only() -> bool:
    return bool(_entries())


def allowed(email: str | None, verified: bool) -> bool:
    """Whether this sign-in identity may use the server."""
    entries = _entries()
    if not entries:
        return True
    if not email or not verified:
        return False
    address = email.strip().lower()
    domain = address.rpartition("@")[2]
    return any(address == e or (e.startswith("@") and domain == e[1:]) for e in entries)
