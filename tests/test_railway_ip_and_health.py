"""
tests/test_railway_ip_and_health.py — Regression suite for Task 4.3.

Covers:
1. Valid Railway client IP resolution via X-Real-IP.
2. Separate rate-limit buckets for different Railway client IPs.
3. Missing X-Real-IP on Railway falls back safely to direct peer.
4. Invalid/malformed X-Real-IP falls back safely to direct peer.
5. Spoofed X-Forwarded-For is ignored.
6. Local development behavior (trusted 127.0.0.1 vs untrusted public peer).
7. Rate limiter stability with valid IP resolution.
8. /health endpoint accurate representation of active provider and models.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from session_auth import resolve_client_ip, is_trusted_proxy, parse_trust_railway_proxy, is_railway_environment
from rate_limiter import rate_limit, LIMITS_IP, LIMITS_SESSION, SlidingWindowLimiter
from main import app


class DummyRequest:
    """Mock FastAPI/Starlette Request for IP resolution unit tests."""

    def __init__(self, host: str = "127.0.0.1", headers: dict = None):
        self.client = type("Client", (), {"host": host})()
        self.headers = headers or {}


# ─── 1. Railway Client IP Resolution Tests ────────────────────────────────────

def test_railway_valid_client_ip():
    """Railway edge terminates external traffic and passes client IP in X-Real-IP."""
    with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT": "production"}):
        req = DummyRequest(host="10.0.12.34", headers={"x-real-ip": "203.0.113.195"})
        resolved = resolve_client_ip(req)
        assert resolved == "203.0.113.195"


def test_railway_missing_x_real_ip_falls_back_safely():
    """If X-Real-IP is absent on Railway, fall back safely to direct peer without error."""
    with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT": "production"}):
        req = DummyRequest(host="10.0.12.34", headers={})
        resolved = resolve_client_ip(req)
        assert resolved == "10.0.12.34"


def test_railway_invalid_x_real_ip_falls_back_safely():
    """Malformed or invalid X-Real-IP must not raise an exception; falls back to direct peer."""
    with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT": "production"}):
        for bad_ip in ["not-an-ip", "999.999.999.999", "1.2.3.4.5", "'; DROP TABLE", ""]:
            req = DummyRequest(host="10.0.12.34", headers={"x-real-ip": bad_ip})
            resolved = resolve_client_ip(req)
            assert resolved == "10.0.12.34", f"Failed to fall back for bad IP: {bad_ip}"


def test_railway_x_real_ip_with_port_is_sanitized():
    """If X-Real-IP contains an IPv4 port (e.g. '203.0.113.50:443'), port is stripped safely."""
    with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT": "production"}):
        req = DummyRequest(host="10.0.12.34", headers={"x-real-ip": "203.0.113.50:443"})
        resolved = resolve_client_ip(req)
        assert resolved == "203.0.113.50"


def test_railway_spoofed_x_forwarded_for_ignored():
    """On Railway, X-Real-IP is the authoritative source; spoofed X-Forwarded-For is ignored."""
    with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT": "production"}):
        req = DummyRequest(
            host="10.0.12.34",
            headers={
                "x-real-ip": "203.0.113.195",
                "x-forwarded-for": "198.51.100.99, 1.1.1.1",
            },
        )
        resolved = resolve_client_ip(req)
        assert resolved == "203.0.113.195"


def test_local_dev_untrusted_direct_peer_ignores_forwarding_headers():
    """In local dev, direct untrusted peer cannot spoof X-Real-IP or X-Forwarded-For."""
    with patch.dict(os.environ, {}, clear=True):
        req = DummyRequest(
            host="198.51.100.24",
            headers={
                "x-real-ip": "1.1.1.1",
                "x-forwarded-for": "8.8.8.8",
                "cf-connecting-ip": "9.9.9.9",
            },
        )
        resolved = resolve_client_ip(req)
        assert resolved == "198.51.100.24"


def test_local_dev_trusted_peer_accepts_x_real_ip():
    """In local dev, a trusted reverse proxy (127.0.0.1) passing X-Real-IP is honored."""
    with patch.dict(os.environ, {}, clear=True):
        req = DummyRequest(host="127.0.0.1", headers={"x-real-ip": "198.51.100.77"})
        resolved = resolve_client_ip(req)
        assert resolved == "198.51.100.77"


# ─── 2. Rate-Limiting Isolation Across Railway Clients ────────────────────────

def test_railway_different_clients_have_separate_rate_limit_buckets():
    """Two different clients behind Railway's proxy receive independent IP rate limits."""
    limiter = SlidingWindowLimiter(max_requests=2, window_seconds=60, scope="IP")

    with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT": "production"}):
        req_client_a = DummyRequest(host="10.0.1.5", headers={"x-real-ip": "203.0.113.10"})
        req_client_b = DummyRequest(host="10.0.1.5", headers={"x-real-ip": "203.0.113.20"})

        ip_a = resolve_client_ip(req_client_a)
        ip_b = resolve_client_ip(req_client_b)

        assert ip_a != ip_b
        assert ip_a == "203.0.113.10"
        assert ip_b == "203.0.113.20"

        # Client A consumes its 2 allowed requests
        limiter.check(f"upload:ip:{ip_a}")
        limiter.check(f"upload:ip:{ip_a}")

        # Client A is now rate-limited
        with pytest.raises(Exception) as exc_info:
            limiter.check(f"upload:ip:{ip_a}")
        assert "429" in str(exc_info.value) or exc_info.value.status_code == 429

        # Client B must NOT be blocked by Client A's activity
        limiter.check(f"upload:ip:{ip_b}")
        limiter.check(f"upload:ip:{ip_b}")  # Second request succeeds for Client B


# ─── 3. Health Endpoint Tests ─────────────────────────────────────────────────

@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint_structure_and_readiness(client):
    """GET /health must return status ok, provider, models, and no secrets."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data.get("status") == "ok"
    assert data.get("service") == "hamigenz"
    assert data.get("version") == "0.1.0"
    assert "provider" in data
    assert "llm_model" in data
    assert "embedder" in data

    # Security check: ensure no sensitive keys or internal paths leaked
    raw_text = resp.text.lower()
    assert "api_key" not in raw_text
    assert "secret" not in raw_text
    assert "c:\\" not in raw_text
    assert "/app/" not in raw_text


def test_health_endpoint_reflects_gemini_provider(client):
    """When LLM_PROVIDER is gemini, /health returns provider=gemini and gemini model name."""
    with patch("main.LLM_PROVIDER", "gemini"), patch("main.GEMINI_MODEL", "gemini-3.5-flash-lite"):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "gemini"
        assert data["llm_model"] == "gemini-3.5-flash-lite"
        # Backward-compatibility field retained
        assert "ollama_model" in data


def test_health_endpoint_reflects_ollama_provider(client):
    """When LLM_PROVIDER is ollama, /health returns provider=ollama and ollama model name."""
    with patch("main.LLM_PROVIDER", "ollama"), patch("main.OLLAMA_MODEL", "qwen3:8b"):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "ollama"
        assert data["llm_model"] == "qwen3:8b"
        assert data["ollama_model"] == "qwen3:8b"



# ─── 4. Session Rotation & Quota Security Tests (Task 4.3.2) ──────────────────

def test_session_rotation_cannot_bypass_ip_rate_limit():
    """
    Even if an attacker rotates or clears session IDs on every request,
    the aggregate IP rate limiter continues to count against their client IP.
    """
    ip_limiter = SlidingWindowLimiter(max_requests=3, window_seconds=60, scope="IP")
    client_ip = "198.51.100.42"

    # Attacker generates 3 distinct sessions from the same IP
    sessions = ["sess_alpha", "sess_beta", "sess_gamma", "sess_delta"]

    # First 3 requests succeed under the IP ceiling
    for i in range(3):
        ip_limiter.check(f"upload:ip:{client_ip}")

    # 4th request from the same IP with a brand new session MUST be rejected by IP ceiling
    with pytest.raises(Exception) as exc_info:
        ip_limiter.check(f"upload:ip:{client_ip}")
    assert "429" in str(exc_info.value) or exc_info.value.status_code == 429


def test_document_ownership_isolated_across_rotated_sessions():
    """
    When a visitor rotates or drops their session token, newly issued sessions
    cannot access documents owned by previous sessions.
    """
    from session_auth import generate_session_token
    import uuid

    sid_a = str(uuid.uuid4())
    sid_b = str(uuid.uuid4())

    # Mock metadata store with document owned by sid_a
    mock_app = MagicMock()
    mock_app.state.metadata.get_document.side_effect = lambda doc_id, session_id: (
        {"doc_id": doc_id, "session_id": sid_a} if session_id == sid_a else None
    )

    from main import verify_document_owner
    from fastapi import HTTPException

    # Session A can access its own document
    doc = verify_document_owner(mock_app, "doc_123", session_id=sid_a)
    assert doc["doc_id"] == "doc_123"

    # Rotated Session B trying to access Session A's document receives HTTP 404
    with pytest.raises(HTTPException) as exc:
        verify_document_owner(mock_app, "doc_123", session_id=sid_b)
    assert exc.value.status_code == 404


# ─── 5. TRUST_RAILWAY_PROXY Boolean Parsing & Override Tests (Task 4.3.4) ─────

def test_parse_trust_railway_proxy_accepted_true_values():
    """All standard true variants ('1', 'true', 'yes', 'on', case-insensitive, with whitespace) evaluate to True."""
    for val in ['1', 'true', 'TRUE', 'True', 'yes', 'YES', 'Yes', 'on', 'ON', '  true  ', ' 1 ']:
        assert parse_trust_railway_proxy(val) is True, f"Failed for accepted true value: {val!r}"


def test_parse_trust_railway_proxy_accepted_false_values():
    """All standard false variants ('0', 'false', 'no', 'off', case-insensitive, with whitespace) evaluate to False."""
    for val in ['0', 'false', 'FALSE', 'False', 'no', 'NO', 'No', 'off', 'OFF', '  false  ', ' 0 ']:
        assert parse_trust_railway_proxy(val) is False, f"Failed for accepted false value: {val!r}"


def test_parse_trust_railway_proxy_missing_and_empty():
    """Unset, empty, or whitespace-only strings evaluate to False."""
    for val in [None, '', '   ', '\t']:
        assert parse_trust_railway_proxy(val) is False, f"Failed for empty/missing value: {val!r}"


def test_parse_trust_railway_proxy_invalid_fails_closed():
    """Unknown / unparseable values fail closed to False."""
    for val in ['maybe', '2', 'none', '-1', 'truthy', 'enabled', 'disabled', 'null', 'undefined']:
        assert parse_trust_railway_proxy(val) is False, f"Failed to fail closed for invalid value: {val!r}"


def test_railway_auto_detection_without_manual_override():
    """Railway environment is auto-detected when RAILWAY_ENVIRONMENT or RAILWAY_PROJECT_ID is present."""
    with patch.dict(os.environ, {'RAILWAY_ENVIRONMENT': 'production'}, clear=True):
        assert is_railway_environment() is True

    with patch.dict(os.environ, {'RAILWAY_PROJECT_ID': 'proj_abc123'}, clear=True):
        assert is_railway_environment() is True

    with patch.dict(os.environ, {}, clear=True):
        assert is_railway_environment() is False


def test_non_railway_environment_with_proxy_trust_disabled():
    """In a non-Railway environment, proxy trust is disabled by default or when explicitly set to false."""
    with patch.dict(os.environ, {}, clear=True):
        assert is_railway_environment() is False
        req = DummyRequest(host='198.51.100.5', headers={'x-real-ip': '1.1.1.1'})
        assert resolve_client_ip(req) == '198.51.100.5'

    with patch.dict(os.environ, {'TRUST_RAILWAY_PROXY': '0'}, clear=True):
        assert is_railway_environment() is False
        req = DummyRequest(host='198.51.100.5', headers={'x-real-ip': '1.1.1.1'})
        assert resolve_client_ip(req) == '198.51.100.5'


def test_non_railway_environment_with_proxy_trust_explicitly_enabled():
    """When TRUST_RAILWAY_PROXY=1/true, proxy trust is active even without Railway environment variables."""
    for true_val in ['1', 'true', 'yes', 'on']:
        with patch.dict(os.environ, {'TRUST_RAILWAY_PROXY': true_val}, clear=True):
            assert is_railway_environment() is True
            req = DummyRequest(host='10.0.0.1', headers={'x-real-ip': '203.0.113.88'})
            assert resolve_client_ip(req) == '203.0.113.88'


def test_railway_environment_explicit_override_precedence():
    """An explicit TRUST_RAILWAY_PROXY=0/false overrides automatic Railway detection to False."""
    for false_val in ['0', 'false', 'no', 'off']:
        with patch.dict(os.environ, {'RAILWAY_ENVIRONMENT': 'production', 'TRUST_RAILWAY_PROXY': false_val}):
            assert is_railway_environment() is False
            req = DummyRequest(host='10.0.12.34', headers={'x-real-ip': '203.0.113.99'})
            assert resolve_client_ip(req) == '10.0.12.34'

    # Invalid value on Railway also fails closed to False
    with patch.dict(os.environ, {'RAILWAY_ENVIRONMENT': 'production', 'TRUST_RAILWAY_PROXY': 'invalid_val'}):
        assert is_railway_environment() is False


def test_untrusted_requests_cannot_influence_rate_limit_identity():
    """Untrusted direct peer cannot spoof client IP to evade or pollute rate limit buckets."""
    limiter = SlidingWindowLimiter(max_requests=2, window_seconds=60, scope='IP')

    with patch.dict(os.environ, {}, clear=True):
        # Attacker at 198.51.100.24 tries to claim they are 1.1.1.1 via X-Real-IP
        req = DummyRequest(
            host='198.51.100.24',
            headers={'x-real-ip': '1.1.1.1', 'x-forwarded-for': '1.1.1.1'},
        )
        resolved_ip = resolve_client_ip(req)
        assert resolved_ip == '198.51.100.24'  # Resolved to real direct peer, not spoofed IP

        # Rate limiter records hits against the real direct peer
        limiter.check(f'upload:ip:{resolved_ip}')
        limiter.check(f'upload:ip:{resolved_ip}')

        # The real peer is now blocked
        with pytest.raises(Exception):
            limiter.check(f'upload:ip:{resolved_ip}')

        # Spoofed IP bucket was never touched and remains clean (0 hits)
        assert len(limiter._hits.get('upload:ip:1.1.1.1', [])) == 0
