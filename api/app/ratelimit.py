"""W5 — rate limiting for ``/auth/*`` and sign-in failures, per client address.

An in-process sliding window: enough to blunt scripted hammering of the OAuth endpoints (each
callback costs two outbound provider requests) beyond what an edge proxy gives. State is per
process, so with N machines the effective ceiling is N x the limit; that is acceptable for a
defence-in-depth layer. Per-account export limits (the money-costly resource) live in the shared
database ledger (``usage.py``) and are unaffected.

The client address is the TCP peer unless ``EXAM_CLIENT_IP_HEADER`` names a header the platform
overwrites (``Fly-Client-IP`` on Fly, ``CF-Connecting-IP`` behind Cloudflare). Never set it where a
client can reach the app directly: the header would then be attacker-controlled.
"""

from __future__ import annotations

import os
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException, Request

_MAX_KEYS = 10_000


@dataclass(frozen=True)
class AuthLimits:
    requests_per_minute: int  # every /auth/* request
    attempts_per_minute: int  # login + callback (each callback calls the provider twice)
    failures_per_15min: int  # failed sign-ins (bad state, provider rejected), then locked out


def limits_from_env() -> AuthLimits:
    def num(name: str, default: int) -> int:
        try:
            return max(0, int(os.environ.get(name, default)))
        except ValueError:
            return default

    return AuthLimits(
        num("EXAM_AUTH_LIMIT_PER_MINUTE", 300),
        num("EXAM_AUTH_ATTEMPTS_PER_MINUTE", 30),
        num("EXAM_AUTH_FAILURES_PER_15_MIN", 20),
    )


class SlidingWindow:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._events: dict[str, deque[float]] = {}

    def _live(self, key: str, window: float) -> deque[float]:
        events = self._events.get(key)
        if events is None:
            if len(self._events) >= _MAX_KEYS:  # bound memory: drop keys with nothing recent
                horizon = self._clock() - 3600
                self._events = {k: v for k, v in self._events.items() if v and v[-1] > horizon}
            events = self._events.setdefault(key, deque())
        cutoff = self._clock() - window
        while events and events[0] <= cutoff:
            events.popleft()
        return events

    def retry_after(self, key: str, limit: int, window: float) -> int:
        """Seconds until ``key`` is under ``limit`` again (0 = under it now). Records nothing."""
        if limit <= 0:
            return 0
        events = self._live(key, window)
        if len(events) < limit:
            return 0
        return max(1, int(events[len(events) - limit] + window - self._clock()) + 1)

    def record(self, key: str, window: float) -> None:
        self._live(key, window).append(self._clock())

    def hit(self, key: str, limit: int, window: float) -> int:
        """Count one event unless over the limit; returns the wait in seconds (0 = allowed)."""
        wait = self.retry_after(key, limit, window)
        if wait == 0:
            self.record(key, window)
        return wait

    def reset(self) -> None:
        self._events.clear()


limiter = SlidingWindow()


def client_ip(request: Request) -> str:
    header = os.environ.get("EXAM_CLIENT_IP_HEADER", "").strip()
    if header and (value := request.headers.get(header)):
        return value.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def limit_auth(request: Request) -> None:
    """Router dependency for all of ``/auth/*``: a generous per-address ceiling."""
    wait = limiter.hit(f"auth:{client_ip(request)}", limits_from_env().requests_per_minute, 60)
    if wait:
        raise HTTPException(
            status_code=429, detail="too many requests", headers={"Retry-After": str(wait)}
        )


def sign_in_wait(request: Request) -> int:
    """Count a login/callback attempt; seconds to wait if the address is over a sign-in limit."""
    limits, ip = limits_from_env(), client_ip(request)
    locked = limiter.retry_after(f"authfail:{ip}", limits.failures_per_15min, 900)
    return locked or limiter.hit(f"attempt:{ip}", limits.attempts_per_minute, 60)


def record_sign_in_failure(request: Request) -> None:
    limiter.record(f"authfail:{client_ip(request)}", 900)
