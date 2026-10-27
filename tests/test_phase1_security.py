"""
hamiGenZ — Phase 1 Security & Access Control Regression Suite.

Verifies:
1. Cryptographically signed anonymous session lifecycle and transport.
2. Cross-user document isolation (reading, viewing, searching, mutating, deleting).
3. Query isolation (preventing cross-user vector search leakage).
4. Dual-tier sliding-window rate limiting (3 uploads/min per session, Retry-After header, shared IP handling).
5. Proxy trust boundary and IP resolution (preventing spoofed header bypass).
6. CSRF mitigation on cookie-authenticated mutations.
7. Legacy database record quarantine.
"""

import os
import sys
import io
import time
import uuid
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend modules are importable
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from main import app
from session_auth import (
    generate_session_token,
    verify_session_token,
    resolve_client_ip,
    is_trusted_proxy,
    SESSION_COOKIE_NAME,
    SESSION_HEADER_NAME,
)
from rate_limiter import SlidingWindowLimiter


@pytest.fixture
def client():
    """TestClient with lifespan triggered."""
    with TestClient(app) as c:
        yield c


def _create_sample_png_bytes() -> bytes:
    """Generate a valid PNG image over 100 bytes."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (150, 150), color=(245, 245, 245))
    d = ImageDraw.Draw(img)
    d.text((10, 20), "Verified citizen registration sample document.", fill=(10, 10, 10))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ─── 1. Session Lifecycle & Transport ─────────────────────────────────────────

class TestSessionLifecycle:
    def test_first_time_visitor_receives_signed_session(self, client):
        """First request must receive X-Session-Token and cookie without refresh."""
        resp = client.get("/health")
        assert resp.status_code == 200
        
        # Verify response header
        token = resp.headers.get("X-Session-Token")
        assert token is not None
        assert token.startswith("s_")
        
        # Verify cookie
        assert SESSION_COOKIE_NAME in resp.cookies
        assert resp.cookies[SESSION_COOKIE_NAME] == token

        # Verify signature validity
        sid = verify_session_token(token)
        assert sid is not None

    def test_existing_valid_token_is_preserved(self, client):
        """Providing a valid session token in header must retain that session ID."""
        orig_sid = str(uuid.uuid4())
        orig_token = generate_session_token(orig_sid)

        resp = client.get("/health", headers={SESSION_HEADER_NAME: orig_token})
        assert resp.status_code == 200
        assert resp.headers.get("X-Session-Token") == orig_token

    def test_tampered_token_is_gracefully_refreshed(self, client):
        """A forged or tampered token must be rejected and replaced safely."""
        tampered_token = f"s_{uuid.uuid4()}.{int(time.time())}.bad_signature_here_1234567890"

        resp = client.get("/health", headers={SESSION_HEADER_NAME: tampered_token})
        assert resp.status_code == 200
        new_token = resp.headers.get("X-Session-Token")
        assert new_token is not None
        assert new_token != tampered_token
        assert verify_session_token(new_token) is not None

    def test_expired_token_is_rejected_and_refreshed(self, client):
        """An expired token (>24h old) must be rejected and refreshed."""
        old_time = int(time.time()) - 100000
        old_token = generate_session_token(str(uuid.uuid4()))
        # Manually construct expired token
        parts = old_token.split(".")
        expired_token = f"{parts[0]}.{old_time}.{parts[2]}"

        resp = client.get("/health", headers={SESSION_HEADER_NAME: expired_token})
        assert resp.status_code == 200
        refreshed_token = resp.headers.get("X-Session-Token")
        assert refreshed_token != expired_token


# ─── 2. Cross-User Document Access & Deletion Isolation ──────────────────────

class TestCrossUserDocumentIsolation:
    def test_two_sessions_cannot_access_or_delete_each_others_documents(self, client):
        """
        User A uploads document A.
        User B (different session) must receive 404 when attempting to:
        - View document A
        - View document A page image
        - Search text in document A
        - Set form fields on document A
        - Delete document A
        - List documents (must not see document A)
        """
        # Session A
        token_a = generate_session_token(str(uuid.uuid4()))
        headers_a = {SESSION_HEADER_NAME: token_a, "x-requested-with": "XMLHttpRequest"}

        # Session B
        token_b = generate_session_token(str(uuid.uuid4()))
        headers_b = {SESSION_HEADER_NAME: token_b, "x-requested-with": "XMLHttpRequest"}

        # User A uploads a document
        png_bytes = _create_sample_png_bytes()
        upload_resp = client.post(
            "/upload",
            files={"file": ("citizen_form.png", io.BytesIO(png_bytes), "image/png")},
            headers=headers_a,
        )
        assert upload_resp.status_code == 200, upload_resp.text
        doc_a_id = upload_resp.json()["doc_id"]

        # User A can view their own document
        view_a = client.get(f"/documents/{doc_a_id}/viewer", headers=headers_a)
        assert view_a.status_code == 200
        assert view_a.json()["doc_id"] == doc_a_id

        # User A sees doc in their list
        list_a = client.get("/documents", headers=headers_a)
        assert list_a.status_code == 200
        assert any(d["doc_id"] == doc_a_id for d in list_a.json())

        # ─── User B Attempts Unauthorized Access (All must 404) ───

        # 1. Viewer access by User B
        view_b = client.get(f"/documents/{doc_a_id}/viewer", headers=headers_b)
        assert view_b.status_code == 404

        # 2. Page image access by User B
        img_b = client.get(f"/documents/{doc_a_id}/page/1/image", headers=headers_b)
        assert img_b.status_code == 404

        # 3. Search text access by User B
        search_b = client.get(f"/documents/{doc_a_id}/search-text?query=Nepal", headers=headers_b)
        assert search_b.status_code == 404

        # 4. Form fields modification by User B
        fields_b = client.post(
            f"/documents/{doc_a_id}/form-fields",
            json={"values": [{"label": "Name", "value": "Hacked"}]},
            headers=headers_b,
        )
        assert fields_b.status_code == 404

        # 5. Unauthorized deletion by User B
        del_b = client.post(f"/documents/{doc_a_id}", headers=headers_b)  # POST instead of DELETE or DELETE
        del_b_real = client.delete(f"/documents/{doc_a_id}", headers=headers_b)
        assert del_b_real.status_code == 404

        # 6. Global list isolation: User B must not see doc_A in /documents
        list_b = client.get("/documents", headers=headers_b)
        assert list_b.status_code == 200
        assert not any(d["doc_id"] == doc_a_id for d in list_b.json())

        # Verify Document A is still fully intact for User A
        verify_a = client.get(f"/documents/{doc_a_id}/viewer", headers=headers_a)
        assert verify_a.status_code == 200

        # Cleanup: User A can delete their own document
        del_a = client.delete(f"/documents/{doc_a_id}", headers=headers_a)
        assert del_a.status_code == 200


# ─── 3. Query Isolation ───────────────────────────────────────────────────────

class TestQueryIsolation:
    def test_unspecified_ask_never_retrieves_other_sessions_vectors(self, client):
        """
        When doc_id is omitted in /ask, the query must NEVER search across
        another session's uploaded documents.
        """
        # Session A uploads a document
        token_a = generate_session_token(str(uuid.uuid4()))
        headers_a = {SESSION_HEADER_NAME: token_a, "x-requested-with": "XMLHttpRequest"}

        png_bytes = _create_sample_png_bytes()
        upload_resp = client.post(
            "/upload",
            files={"file": ("private_citizen_doc.png", io.BytesIO(png_bytes), "image/png")},
            headers=headers_a,
        )
        assert upload_resp.status_code == 200
        doc_a_id = upload_resp.json()["doc_id"]

        # Session B has no documents uploaded
        token_b = generate_session_token(str(uuid.uuid4()))
        headers_b = {SESSION_HEADER_NAME: token_b, "x-requested-with": "XMLHttpRequest"}

        # Session B asks a document-like question with no doc_id
        ask_resp = client.post(
            "/ask",
            json={"question": "What is in the uploaded document?", "doc_id": None},
            headers=headers_b,
        )
        assert ask_resp.status_code == 200
        body = ask_resp.json()
        
        # Evidence must NOT contain doc_a_id
        for citation in body.get("citations", []):
            assert citation.get("doc_id") != doc_a_id

        # Cleanup
        client.delete(f"/documents/{doc_a_id}", headers=headers_a)


# ─── 4. Rate Limiting Boundaries ─────────────────────────────────────────────

class TestRateLimitingBoundaries:
    def test_upload_rate_limit_3_per_minute_with_retry_after(self, client):
        """
        Session limit: 3 uploads allowed in 60s; 4th upload rejected with 429 and Retry-After.
        """
        session_id = str(uuid.uuid4())
        token = generate_session_token(session_id)
        headers = {SESSION_HEADER_NAME: token, "x-requested-with": "XMLHttpRequest"}
        png_bytes = _create_sample_png_bytes()

        created_docs = []
        try:
            # 1st upload -> 200
            r1 = client.post("/upload", files={"file": ("d1.png", io.BytesIO(png_bytes), "image/png")}, headers=headers)
            assert r1.status_code == 200
            created_docs.append(r1.json()["doc_id"])

            # 2nd upload -> 200
            r2 = client.post("/upload", files={"file": ("d2.png", io.BytesIO(png_bytes), "image/png")}, headers=headers)
            assert r2.status_code == 200
            created_docs.append(r2.json()["doc_id"])

            # 3rd upload -> 200
            r3 = client.post("/upload", files={"file": ("d3.png", io.BytesIO(png_bytes), "image/png")}, headers=headers)
            assert r3.status_code == 200
            created_docs.append(r3.json()["doc_id"])

            # 4th upload -> 429 Too Many Requests
            r4 = client.post("/upload", files={"file": ("d4.png", io.BytesIO(png_bytes), "image/png")}, headers=headers)
            assert r4.status_code == 429
            assert "Retry-After" in r4.headers
            retry_after = int(r4.headers["Retry-After"])
            assert 1 <= retry_after <= 60
            assert "Rate limit exceeded" in r4.json()["detail"]

        finally:
            for doc_id in created_docs:
                client.delete(f"/documents/{doc_id}", headers=headers)

    def test_shared_ip_separate_session_quotas(self, client):
        """
        Two distinct sessions originating from the same client IP (e.g. NAT/Cybercafe)
        must retain independent session quotas.
        """
        limiter = SlidingWindowLimiter(max_requests=2, window_seconds=60, scope="session")

        # Session 1 makes 2 requests -> both succeed
        limiter.check("upload:sess:user_session_1")
        limiter.check("upload:sess:user_session_1")

        # Session 1 makes 3rd request -> blocked
        with pytest.raises(Exception) as exc:
            limiter.check("upload:sess:user_session_1")
        assert exc.value.status_code == 429

        # Session 2 on the same IP must still be allowed to make requests!
        limiter.check("upload:sess:user_session_2")
        limiter.check("upload:sess:user_session_2")


# ─── 5. Proxy Trust & IP Resolution ──────────────────────────────────────────

class TestProxyTrustAndIPResolution:
    def test_untrusted_direct_peer_ignores_forged_forwarded_headers(self):
        """
        A direct connection from an untrusted public IP with forged headers
        must NOT use the forged IP for rate limiting.
        """
        class DummyRequest:
            client = type("Client", (), {"host": "198.51.100.24"})()  # Public untrusted IP
            headers = {"x-forwarded-for": "10.0.0.1, 203.0.113.5", "cf-connecting-ip": "1.1.1.1"}

        resolved = resolve_client_ip(DummyRequest())
        assert resolved == "198.51.100.24"  # Forged headers must be ignored

    def test_trusted_proxy_peer_parses_real_client_ip(self):
        """
        A connection from a trusted proxy (e.g. 127.0.0.1) must safely extract
        the first untrusted upstream IP from X-Forwarded-For.
        """
        class DummyRequest:
            client = type("Client", (), {"host": "127.0.0.1"})()  # Trusted local proxy
            headers = {"x-forwarded-for": "203.0.113.88, 127.0.0.1"}

        resolved = resolve_client_ip(DummyRequest())
        assert resolved == "203.0.113.88"


# ─── 6. CSRF Mitigation ──────────────────────────────────────────────────────

class TestCSRFProtection:
    def test_cookie_authenticated_mutation_without_custom_headers_blocked_on_unapproved_origin(self, client):
        """
        Cross-site request attempting a mutating action with only cookies
        and an unapproved origin must be rejected with 403.
        """
        token = generate_session_token(str(uuid.uuid4()))
        client.cookies.set(SESSION_COOKIE_NAME, token)

        # Mutating request without X-Session-Token from rogue origin
        resp = client.post(
            "/feedback",
            json={"question": "Test", "rating": 1},
            headers={"origin": "https://malicious-site.example.com"},
        )
        assert resp.status_code == 403
        assert "CSRF" in resp.json()["detail"]

    def test_mutation_with_session_token_header_from_unapproved_origin_is_allowed(self, client):
        """
        Request from an unapproved origin that carries a valid X-Session-Token header
        is allowed. The token proves the caller already possesses the session credential,
        so CSRF (which relies on the victim's credentials being used without their
        knowledge) is not possible.
        NOTE: X-Requested-With alone is NOT sufficient — only X-Session-Token exempts.
        """
        token = generate_session_token(str(uuid.uuid4()))
        resp = client.post(
            "/feedback",
            json={"question": "Test", "rating": 1},
            headers={
                SESSION_HEADER_NAME: token,
                "origin": "https://any-origin.example.com",
            },
        )
        assert resp.status_code == 200

    def test_mutation_with_only_x_requested_with_from_unapproved_origin_is_blocked(self, client):
        """
        X-Requested-With alone from an unapproved origin must be rejected.
        An attacker can set this header from a non-browser client without going
        through CORS preflight, so it provides no CSRF guarantee on its own.
        """
        resp = client.post(
            "/feedback",
            json={"question": "Test", "rating": 1},
            headers={
                "origin": "https://malicious-site.example.com",
                "x-requested-with": "XMLHttpRequest",
            },
        )
        assert resp.status_code == 403, (
            f"SECURITY BUG: X-Requested-With alone bypassed CSRF, got {resp.status_code}"
        )


# ─── 7. Legacy Database Quarantine ───────────────────────────────────────────

class TestLegacyDataQuarantine:
    def test_legacy_quarantined_records_inaccessible_to_new_sessions(self, client):
        """
        Legacy records marked '__quarantined_legacy__' must never be listed or
        accessible to any regular user session.
        """
        # Directly insert a quarantined legacy document into MetadataStore
        app.state.metadata.add_document(
            doc_id="legacy-unowned-doc-123",
            filename="legacy_file.pdf",
            filepath=str(BACKEND_DIR / "data" / "uploads" / "legacy.pdf"),
            page_count=1,
            session_id="__quarantined_legacy__",
        )

        user_token = generate_session_token(str(uuid.uuid4()))
        headers = {SESSION_HEADER_NAME: user_token}

        # 1. Must not appear in user's /documents list
        docs = client.get("/documents", headers=headers).json()
        assert not any(d["doc_id"] == "legacy-unowned-doc-123" for d in docs)

        # 2. Must return 404 on direct access
        resp = client.get("/documents/legacy-unowned-doc-123/viewer", headers=headers)
        assert resp.status_code == 404

        # Cleanup
        app.state.metadata.delete_document("legacy-unowned-doc-123")
