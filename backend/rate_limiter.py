"""
hamigenz — Lightweight in-memory rate limiting for expensive endpoints.

Local/free solution (no external dependency) appropriate for the
development phase. Limits are per client IP per protected route group,
using a sliding window. Configure via env:

    RATE_LIMIT_UPLOAD   = "10/3600"   (default)
    RATE_LIMIT_AI       = "30/3600"   (/ask, /explain, /ask-general)
    RATE_LIMIT_SEARCH   = "120/60"    (search-text)

Format: "<max requests>/<window seconds>".
Set a variable to "off" to disable that limit.
"""
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


def _parse_limit(raw: str, default: tuple[int, int]) -> tuple[int, int]:
    """Parse '<n>/<seconds>'; return (max_requests, window_seconds)."""
    try:
        n, window = raw.split("/")
        return int(n), int(window)
    except Exception:
        return default


LIMITS: dict[str, tuple[int, int]] = {
    "upload": _parse_limit(os.getenv("RATE_LIMIT_UPLOAD", "10/3600"), (10, 3600)),
    "ai": _parse_limit(os.getenv("RATE_LIMIT_AI", "30/3600"), (30, 3600)),
    "search": _parse_limit(os.getenv("RATE_LIMIT_SEARCH", "120/60"), (120, 60)),
}


class SlidingWindowLimiter:
    """Thread-safe in-memory sliding-window counter per key."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Raise 429 if the key exceeded the limit; otherwise record a hit."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            cutoff = now - self.window
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= self.max_requests:
                retry_after = int(hits[0] + self.window - now) + 1
                raise HTTPException(
                    429,
                    f"Rate limit exceeded. Try again in {retry_after}s.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)
            # Opportunistic cleanup: drop fully stale keys
            if len(self._hits) > 10000:
                stale = [k for k, v in self._hits.items() if not v or v[-1] < cutoff]
                for k in stale:
                    del self._hits[k]


_limiters: dict[str, SlidingWindowLimiter] = {}


def _limiter(group: str) -> SlidingWindowLimiter | None:
    limit = LIMITS.get(group)
    if not limit or limit[0] <= 0:
        return None
    if group not in _limiters:
        _limiters[group] = SlidingWindowLimiter(limit[0], limit[1])
    return _limiters[group]


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit(group: str):
    """FastAPI dependency factory: enforce the named limit group per IP."""

    async def _dependency(request: Request) -> None:
        limiter = _limiter(group)
        if limiter is None:
            return
        limiter.check(f"{group}:{_client_ip(request)}")

    return _dependency
