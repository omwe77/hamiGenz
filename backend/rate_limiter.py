"""
hamigenz — Dual-Tier Sliding-Window Rate Limiter.

Protects against abuse while accommodating shared-IP environments (NAT, campuses, offices)
by enforcing:
1. Per-session quota (e.g. 3 uploads / 60 seconds per session).
2. Per-IP aggregate abuse ceiling (e.g. 15 uploads / 60 seconds per IP).

Resolves client IP strictly through proxy-aware trust validation (session_auth.resolve_client_ip).
"""

import os
import threading
import time
from collections import defaultdict, deque
from typing import Optional, Tuple
from fastapi import HTTPException, Request

from session_auth import resolve_client_ip, get_or_create_session


def _parse_limit(raw: str, default: Tuple[int, int]) -> Tuple[int, int]:
    """Parse '<n>/<seconds>'; return (max_requests, window_seconds)."""
    try:
        n, window = raw.split("/")
        return int(n), int(window)
    except Exception:
        return default


# Limits are configured as (session_max/seconds, ip_max/seconds)
LIMITS_SESSION: dict[str, Tuple[int, int]] = {
    # 3 uploads per minute per session as required by technical lead
    "upload": _parse_limit(os.getenv("RATE_LIMIT_UPLOAD_SESSION", "3/60"), (3, 60)),
    "ai": _parse_limit(os.getenv("RATE_LIMIT_AI_SESSION", "10/60"), (10, 60)),
    "search": _parse_limit(os.getenv("RATE_LIMIT_SEARCH_SESSION", "60/60"), (60, 60)),
}

LIMITS_IP: dict[str, Tuple[int, int]] = {
    # Aggregate IP protection: 15 uploads/min per IP
    "upload": _parse_limit(os.getenv("RATE_LIMIT_UPLOAD_IP", "15/60"), (15, 60)),
    "ai": _parse_limit(os.getenv("RATE_LIMIT_AI_IP", "30/60"), (30, 60)),
    "search": _parse_limit(os.getenv("RATE_LIMIT_SEARCH_IP", "120/60"), (120, 60)),
}


class SlidingWindowLimiter:
    """Thread-safe in-memory sliding-window counter per key."""

    def __init__(self, max_requests: int, window_seconds: int, scope: str = "request"):
        self.max_requests = max_requests
        self.window = window_seconds
        self.scope = scope
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, custom_message: Optional[str] = None) -> None:
        """Raise 429 if the key exceeded the limit; otherwise record a hit."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            cutoff = now - self.window
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= self.max_requests:
                retry_after = max(1, int(hits[0] + self.window - now) + 1)
                msg = custom_message or (
                    f"Rate limit exceeded for {self.scope}. "
                    f"Limit: {self.max_requests} requests per {self.window}s. "
                    f"Try again in {retry_after}s."
                )
                raise HTTPException(
                    status_code=429,
                    detail=msg,
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)
            # Opportunistic cleanup
            if len(self._hits) > 10000:
                stale = [k for k, v in self._hits.items() if not v or v[-1] < cutoff]
                for k in stale:
                    del self._hits[k]


_session_limiters: dict[str, SlidingWindowLimiter] = {}
_ip_limiters: dict[str, SlidingWindowLimiter] = {}


def _get_limiter(group: str, is_session: bool) -> Optional[SlidingWindowLimiter]:
    table = LIMITS_SESSION if is_session else LIMITS_IP
    store = _session_limiters if is_session else _ip_limiters
    scope_name = "session" if is_session else "IP"

    limit = table.get(group)
    if not limit or limit[0] <= 0:
        return None
    if group not in store:
        store[group] = SlidingWindowLimiter(limit[0], limit[1], scope=scope_name)
    return store[group]


def rate_limit(group: str):
    """
    FastAPI dependency enforcing dual-tier rate limits:
    1. Check per-session limit first (ensures single session cannot abuse).
    2. Check per-IP aggregate limit second (ensures IP churn cannot exhaust server).
    """

    async def _dependency(request: Request) -> None:
        # Resolve session ID
        session_id = getattr(request.state, "session_id", None)
        if not session_id:
            # Fallback if dependency ran before session middleware
            from session_auth import verify_session_token, SESSION_HEADER_NAME, SESSION_COOKIE_NAME
            tok = request.headers.get(SESSION_HEADER_NAME) or request.cookies.get(SESSION_COOKIE_NAME)
            session_id = verify_session_token(tok) if tok else None
            if not session_id:
                # Untracked anonymous request uses client IP as session key
                session_id = "anon"

        # Check Session Limit
        sess_limiter = _get_limiter(group, is_session=True)
        if sess_limiter:
            sess_limiter.check(f"{group}:sess:{session_id}")

        # Check IP Limit
        ip_limiter = _get_limiter(group, is_session=False)
        if ip_limiter:
            client_ip = resolve_client_ip(request)
            ip_limiter.check(f"{group}:ip:{client_ip}")

    return _dependency
