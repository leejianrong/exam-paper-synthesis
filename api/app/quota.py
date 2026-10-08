"""W1b — export limits.

``check_export_quota`` enforces the per-account export allowance (free product, capped exports
per account — ADR-0022; the ledger is in ``usage.py``). The semaphore bounds how many
headless-Chromium renders run at once so a burst cannot exhaust the machine.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException

from . import usage

_ACQUIRE_TIMEOUT_S = 30.0


def check_export_quota(owner_id: str) -> int | None:
    """Consume one export from ``owner_id``'s allowance, or raise **429** with ``Retry-After``.

    Returns the ledger ticket (pass it to :func:`refund_export` if the export then fails), or
    ``None`` when the account is unlimited.
    """
    limits = usage.limits_from_env()
    if limits.per_day <= 0 and limits.per_minute <= 0:
        return None
    allowance = usage.get_ledger().consume(owner_id, limits)
    if not allowance.allowed:
        what = "this minute" if allowance.reason == "minute" else "in the last 24 hours"
        raise HTTPException(
            status_code=429,
            detail=(
                f"Export limit reached for {what}. Try again in {_human(allowance.retry_after)}."
            ),
            headers={"Retry-After": str(allowance.retry_after)},
        )
    return allowance.ticket


def refund_export(ticket: int | None) -> None:
    """Give back an export that did not produce a PDF."""
    if ticket is not None:
        usage.get_ledger().refund(ticket)


def _human(seconds: int) -> str:
    if seconds < 90:
        return f"{seconds} seconds"
    if seconds < 5400:
        return f"{round(seconds / 60)} minutes"
    return f"{round(seconds / 3600)} hours"


def _limit() -> int:
    try:
        return max(1, int(os.environ.get("EXAM_EXPORT_CONCURRENCY", "2")))
    except ValueError:
        return 2


_SEMAPHORE = threading.BoundedSemaphore(_limit())


@contextmanager
def export_slot() -> Iterator[None]:
    """Hold one of the concurrent-render slots, or 503 if none frees up in time."""
    if not _SEMAPHORE.acquire(timeout=_ACQUIRE_TIMEOUT_S):
        raise HTTPException(status_code=503, detail="export is busy, try again shortly")
    try:
        yield
    finally:
        _SEMAPHORE.release()
