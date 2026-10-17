"""Unit tests for rate_limiter.py — sliding window rate limiting."""
import os
import sys
import pytest
from fastapi import HTTPException

_BACKEND = os.path.dirname(os.path.dirname(__file__))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from rate_limiter import _parse_limit, SlidingWindowLimiter


class TestParseLimit:
    def test_parses_valid_format(self):
        max_req, window = _parse_limit("15/60", (10, 3600))
        assert max_req == 15
        assert window == 60

    def test_falls_back_on_malformed(self):
        default = (10, 3600)
        assert _parse_limit("invalid", default) == default
        assert _parse_limit("10/", default) == default
        assert _parse_limit("/60", default) == default


class TestSlidingWindowLimiter:
    def test_allows_under_limit(self):
        limiter = SlidingWindowLimiter(max_requests=3, window_seconds=60)
        # 3 calls should succeed without exception
        limiter.check("ip-1")
        limiter.check("ip-1")
        limiter.check("ip-1")

    def test_blocks_on_excess(self):
        limiter = SlidingWindowLimiter(max_requests=2, window_seconds=60)
        limiter.check("ip-2")
        limiter.check("ip-2")
        with pytest.raises(HTTPException) as exc:
            limiter.check("ip-2")
        assert exc.value.status_code == 429
        assert "Retry-After" in exc.value.headers

    def test_separate_keys_independent(self):
        limiter = SlidingWindowLimiter(max_requests=1, window_seconds=60)
        limiter.check("client-a")
        # client-b should still be allowed
        limiter.check("client-b")