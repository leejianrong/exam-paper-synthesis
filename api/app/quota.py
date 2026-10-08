"""W1b — export limits.

``check_export_quota`` is the per-account export limit hook: a no-op in W1, filled in by
W3 (free product, capped exports per account — ADR-0022). The semaphore bounds how many
headless-Chromium renders run at once so a burst cannot exhaust the machine.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException

_ACQUIRE_TIMEOUT_S = 30.0


def check_export_quota(owner_id: str) -> None:
    """Raise ``HTTPException(429)`` when ``owner_id`` is over their export allowance (W3)."""


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
