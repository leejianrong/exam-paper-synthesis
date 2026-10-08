"""W4 — production configuration, checked once at boot.

With ``EXAM_ENV=production`` the API refuses to start on a configuration that would be unsafe
or silently broken: the development identity stub enabled, SQLite instead of the shared
database, a non-https public URL (cookies would not be ``Secure``), or no sign-in provider
(nobody could log in). Anything else — local development, tests — is unconstrained.
"""

from __future__ import annotations

import os

from .oauth import enabled_providers


def is_production() -> bool:
    return os.environ.get("EXAM_ENV") == "production"


def production_problems() -> list[str]:
    """What is wrong with the environment for a production boot (empty = fine)."""
    problems: list[str] = []
    if os.environ.get("EXAM_DEV_AUTH") == "1":
        problems.append("EXAM_DEV_AUTH=1 would let anyone act as any owner; unset it")
    if not os.environ.get("EXAM_DATABASE_URL"):
        problems.append("EXAM_DATABASE_URL is not set (production data must live in Postgres)")
    if not os.environ.get("EXAM_PUBLIC_URL", "").startswith("https://"):
        problems.append("EXAM_PUBLIC_URL must be the https:// URL users reach (Secure cookies)")
    if not os.environ.get("EXAM_WEB_URL", "").startswith("https://"):
        problems.append("EXAM_WEB_URL must be the https:// URL of the web app")
    if not enabled_providers():
        problems.append("no sign-in provider is configured (EXAM_OAUTH_*_CLIENT_ID / _SECRET)")
    return problems


def check_production() -> None:
    """Raise ``RuntimeError`` listing every problem when running as production."""
    if not is_production():
        return
    problems = production_problems()
    if problems:
        raise RuntimeError("unsafe production configuration:\n- " + "\n- ".join(problems))
