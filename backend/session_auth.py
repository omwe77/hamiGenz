"""
hamigenz — Session Authentication, Ownership & Proxy-Aware IP Resolution.

Provides:
1. Cryptographically signed anonymous session tokens (HMAC-SHA256).
2. Session transport via both HttpOnly cookies and X-Session-Token headers.
3. Strict document ownership verification.
4. Robust IP resolution with ipaddress CIDR boundary validation for trusted proxies.
"""

import os
import time
import hmac
import uuid
import hashlib
import secrets
import ipaddress
from typing import Optional, Tuple
from fastapi import Request, Response, HTTPException, Depends

# ─── Session Secret Management ───────────────────────────────────────────────
_ENV = os.getenv("ENVIRONMENT", os.getenv("NODE_ENV", "development")).lower()
_CONFIGURED_SECRET = os.getenv("SESSION_SECRET", "").strip()

if _CONFIGURED_SECRET:
    SESSION_SECRET = _CONFIGURED_SECRET.encode("utf-8")
else:
    if _ENV == "production":
        raise RuntimeError(
            "FATAL: SESSION_SECRET environment variable must be set in production mode."
        )
    # In development/testing, generate a strong random secret per process instance.
    # Never fall back to a predictable static string.
    SESSION_SECRET = secrets.token_bytes(32)

SESSION_TTL_SECONDS = 86400  # 24 hours
SESSION_COOKIE_NAME = "hamigenz_session"
SESSION_HEADER_NAME = "x-session-token"

# ─── Trusted Proxy Configuration ─────────────────────────────────────────────
# Comma-separated list of IP addresses or CIDR subnets allowed as upstream proxies.
# Default: loopback only (127.0.0.1 and ::1)
_RAW_TRUSTED = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1").split(",")
TRUSTED_PROXIES: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []

for entry in _RAW_TRUSTED:
    clean = entry.strip()
    if not clean:
        continue
    try:
        if "/" in clean:
            TRUSTED_PROXIES.append(ipaddress.ip_network(clean, strict=False))
        else:
            ip = ipaddress.ip_address(clean)
            TRUSTED_PROXIES.append(
                ipaddress.ip_network(f"{clean}/{32 if ip.version == 4 else 128}", strict=False)
            )
    except ValueError as e:
        print(f"[hamigenz security] Warning: Invalid trusted proxy network '{clean}': {e}")


def is_trusted_proxy(ip_str: str) -> bool:
    """Return True if ip_str is a valid IP inside configured trusted proxy ranges."""
    if not ip_str:
        return False
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        return any(ip in net for net in TRUSTED_PROXIES)
    except ValueError:
        return False


def resolve_client_ip(request: Request) -> str:
    """
    Safely resolve the true client IP address.
    
    Rules:
    1. If the direct peer (request.client.host) is NOT a trusted proxy,
       return direct peer. Never read forwarding headers from untrusted peers.
    2. If direct peer IS trusted, parse X-Forwarded-For right-to-left.
       Return the first untrusted IP found.
    3. CF-Connecting-IP is respected only when direct peer is a trusted proxy.
    """
    direct_peer = request.client.host if (request.client and request.client.host) else "127.0.0.1"

    if not is_trusted_proxy(direct_peer):
        # Untrusted direct peer — headers could be spoofed, ignore them completely
        return direct_peer

    # Peer is trusted: check CF-Connecting-IP first if valid IP
    cf_connecting_ip = request.headers.get("cf-connecting-ip")
    if cf_connecting_ip:
        cf_clean = cf_connecting_ip.strip()
        try:
            ipaddress.ip_address(cf_clean)
            return cf_clean
        except ValueError:
            pass

    # Check X-Forwarded-For right-to-left
    xff = request.headers.get("x-forwarded-for")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        for candidate in reversed(parts):
            try:
                ip = ipaddress.ip_address(candidate)
                # First non-trusted IP from the right is the client
                if not any(ip in net for net in TRUSTED_PROXIES):
                    return candidate
            except ValueError:
                continue
        # If all hops were trusted proxies, return the leftmost valid hop
        if parts:
            try:
                ipaddress.ip_address(parts[0])
                return parts[0]
            except ValueError:
                pass

    return direct_peer


# ─── Cryptographic Session Token Functions ───────────────────────────────────

def generate_session_token(session_id: Optional[str] = None) -> str:
    """Create a signed session token: s_<uuid>.<timestamp>.<hmac_hex>."""
    sid = session_id or str(uuid.uuid4())
    ts = int(time.time())
    payload = f"{sid}:{ts}".encode("utf-8")
    sig = hmac.new(SESSION_SECRET, payload, hashlib.sha256).hexdigest()[:32]
    return f"s_{sid}.{ts}.{sig}"


def verify_session_token(token: str) -> Optional[str]:
    """
    Verify signature and expiration of a session token.
    Returns session_id if valid, or None if invalid or expired.
    """
    if not token or not token.startswith("s_"):
        return None
    raw = token[2:]
    parts = raw.split(".")
    if len(parts) != 3:
        return None
    sid, ts_str, provided_sig = parts
    try:
        ts = int(ts_str)
    except ValueError:
        return None

    now = int(time.time())
    # Reject future timestamps beyond 60s clock skew
    if ts > now + 60:
        return None
    # Reject expired sessions
    if now - ts > SESSION_TTL_SECONDS:
        return None

    # Verify signature
    payload = f"{sid}:{ts}".encode("utf-8")
    expected_sig = hmac.new(SESSION_SECRET, payload, hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(provided_sig, expected_sig):
        return None

    # Verify UUID format
    try:
        uuid.UUID(sid)
    except ValueError:
        return None

    return sid


def get_or_create_session(request: Request, response: Response) -> Tuple[str, str, bool]:
    """
    Extract or create session.
    Returns: (session_id, token_str, is_new)
    Sets response cookie and X-Session-Token header.
    """
    # 1. Try X-Session-Token header
    header_token = request.headers.get(SESSION_HEADER_NAME)
    sid = verify_session_token(header_token) if header_token else None
    token = header_token

    # 2. Try cookie
    if not sid:
        cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
        sid = verify_session_token(cookie_token) if cookie_token else None
        token = cookie_token

    is_new = False
    if not sid:
        sid = str(uuid.uuid4())
        token = generate_session_token(sid)
        is_new = True

    # Attach to request state for access in endpoints
    request.state.session_id = sid
    request.state.session_token = token

    # Set response header so client API can capture it
    response.headers["X-Session-Token"] = token

    # Set cookie (SameSite=Lax for standard web navigation, Secure in prod)
    is_prod = _ENV == "production"
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="none" if is_prod else "lax",
        secure=is_prod,
        path="/",
    )

    return sid, token, is_new
