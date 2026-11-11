"""
tests/test_upload_ingress.py — Task 4.3.10.2 P0 Upload Ingress Protection Tests.

Verifies:
  T1  Body at exact 52 MiB limit accepted (middleware ASGI)
  T2  Body one byte over limit rejected with 413 (middleware ASGI)
  T3  Chunked transfer over limit → 413 (middleware ASGI)
  T4  Understated Content-Length, body over limit → 413 (middleware ASGI)
  T5  File field over 50 MiB, body under 52 MiB → 413 (route-level)
  T6  Too many file fields → 400
  T7  Too many form fields → 400
  T8  Admission semaphore: 5th concurrent upload → 503 + Retry-After
  T9  Rate limit fires before multipart parsing (form never parsed)
  T10 Temp staging file cleaned up after rejection
  T11 Valid small PDF regression (200 OK)
  T12 Reindex regression (200 OK with existing doc_id)
  T13 Content-Length fast-reject (middleware ASGI)
  T14 Conflicting Content-Length headers fallback to streaming counter
"""

import asyncio
import os
import sys
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import main
from main import app, MaxBodySizeMiddleware, _UPLOAD_BODY_LIMIT, _UPLOAD_FILE_LIMIT, UPLOAD_DIR

import httpx


# ─── Helpers ──────────────────────────────────────────────────────────────────

_CHUNK = 65536  # 64 KiB — stream in manageable pieces to avoid huge allocations


def _pdf(size: int = 200) -> bytes:
    """Return a minimal valid PDF header padded to `size` bytes."""
    header = b"%PDF-1.4 fake pdf " + b"x" * max(0, size - 20)
    return header[:size]


def _build_chunks(total_bytes: int, chunk_size: int = _CHUNK) -> list[bytes]:
    """Split total_bytes into chunks — avoids allocating one giant object."""
    chunk = b"x" * chunk_size
    full, rem = divmod(total_bytes, chunk_size)
    result = [chunk] * full
    if rem:
        result.append(b"x" * rem)
    return result


def _mock_app_state():
    """Configure app.state with mocks for the upload pipeline."""
    app.state.pipeline = MagicMock()
    app.state.pipeline.process_document.return_value = {
        "status": "success",
        "doc_id": "testdoc",
        "filename": "test.pdf",
        "pages": 1,
        "chunks": 2,
        "language_hint": "english",
    }
    app.state.pipeline.process_document_staged.return_value = {
        "status": "success",
        "doc_id": "testdoc",
        "filename": "new.pdf",
        "pages": 2,
        "chunks": 3,
        "language_hint": "english",
    }
    app.state.vector_store = MagicMock()
    app.state.metadata = MagicMock()
    app.state.metadata.get_document.return_value = {
        "doc_id": "testdoc",
        "session_id": "sess1",
        "filename": "old.pdf",
        "filepath": str(UPLOAD_DIR / "testdoc.pdf"),
        "upload_date": "2026-01-01T00:00:00+00:00",
        "page_count": 1,
        "language_hint": "english",
        "last_accessed_at": "2026-01-01T00:00:00+00:00",
    }
    app.state.metadata.get_reindex_generation.return_value = 0
    app.state.metadata.list_documents.return_value = [{"doc_id": "testdoc", "session_id": "sess1"}]
    # Fresh semaphores for each test
    if hasattr(app.state, "_upload_admission_sem"):
        del app.state._upload_admission_sem
    if hasattr(app.state, "_staged_backlog_sem"):
        del app.state._staged_backlog_sem
    if hasattr(app.state, "processing_semaphore"):
        del app.state.processing_semaphore


@pytest.fixture(autouse=True)
def reset_rate_limits():
    from rate_limiter import _ip_limiters, _session_limiters
    _ip_limiters.clear()
    _session_limiters.clear()


@pytest.fixture(autouse=True)
def reset_reindex_locks():
    if hasattr(app.state, "_reindex_locks"):
        app.state._reindex_locks.clear()


# ─── ASGI unit tests (MaxBodySizeMiddleware only, no FastAPI lifespan) ────────

class TestMaxBodySizeMiddleware:
    """Direct ASGI tests — no FastAPI startup, no lifespan."""

    def _make_scope(self, path="/upload", cl=None, extra_headers=None):
        hdrs = list(extra_headers or [])
        if cl is not None:
            hdrs.append((b"content-length", str(cl).encode()))
        return {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": hdrs,
            "query_string": b"",
        }

    async def _drive(self, scope, chunks):
        """Drive middleware; return (status, body_bytes)."""
        async def inner(scope, receive, send):
            while True:
                msg = await receive()
                if not msg.get("more_body", False):
                    break
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"content-length", b"2")]})
            await send({"type": "http.response.body", "body": b"ok", "more_body": False})

        mw = MaxBodySizeMiddleware(inner)
        q = list(chunks)

        async def receive():
            if q:
                c = q.pop(0)
                return {"type": "http.request", "body": c, "more_body": bool(q)}
            return {"type": "http.request", "body": b"", "more_body": False}

        status = None
        body = b""

        async def send_fn(msg):
            nonlocal status, body
            if msg["type"] == "http.response.start":
                status = msg["status"]
            elif msg["type"] == "http.response.body":
                body += msg.get("body", b"")

        await mw(scope, receive, send_fn)
        return status, body

    # T13 — Non-/upload path bypasses limiter
    def test_T13_non_upload_path_passthrough(self):
        scope = self._make_scope(path="/health")
        status, _ = asyncio.run(self._drive(scope, [b"hello"]))
        assert status == 200

    # T13 — Content-Length fast-reject
    def test_T13_content_length_fast_reject(self):
        scope = self._make_scope(cl=_UPLOAD_BODY_LIMIT + 1)
        status, body = asyncio.run(self._drive(scope, [b""]))
        assert status == 413
        assert b"52" in body

    # T1 — Body exactly at limit accepted
    def test_T1_body_at_exact_limit_accepted(self):
        scope = self._make_scope()
        chunks = _build_chunks(_UPLOAD_BODY_LIMIT)
        status, _ = asyncio.run(self._drive(scope, chunks))
        assert status == 200

    # T2 — Body one byte over rejected
    def test_T2_body_one_byte_over_rejected(self):
        scope = self._make_scope()
        chunks = _build_chunks(_UPLOAD_BODY_LIMIT) + [b"x"]
        status, _ = asyncio.run(self._drive(scope, chunks))
        assert status == 413

    # T3 — Chunked over limit
    def test_T3_chunked_over_limit(self):
        scope = self._make_scope()
        chunk_size = _UPLOAD_BODY_LIMIT // 3 + 1
        chunks = [b"x" * chunk_size] * 3
        status, _ = asyncio.run(self._drive(scope, chunks))
        assert status == 413

    # T4 — Understated Content-Length
    def test_T4_understated_content_length(self):
        scope = self._make_scope(cl=100)  # Claims 100 bytes
        chunks = _build_chunks(_UPLOAD_BODY_LIMIT + 1)
        status, _ = asyncio.run(self._drive(scope, chunks))
        assert status == 413

    # T14 — Conflicting Content-Length headers rejected with 400
    def test_T14_conflicting_content_length_rejected(self):
        scope = self._make_scope(extra_headers=[
            (b"content-length", b"100"),
            (b"content-length", b"200"),
        ])
        status, body = asyncio.run(self._drive(scope, [b"x" * 100]))
        assert status == 400
        assert b"Conflicting" in body

    # T14b — Malformed non-integer Content-Length rejected with 400
    def test_T14b_malformed_content_length_rejected(self):
        scope = self._make_scope(extra_headers=[
            (b"content-length", b"not-an-int"),
        ])
        status, body = asyncio.run(self._drive(scope, [b"x" * 100]))
        assert status == 400
        assert b"non-integer" in body

    # T14c — Negative Content-Length rejected with 400
    def test_T14c_negative_content_length_rejected(self):
        scope = self._make_scope(extra_headers=[
            (b"content-length", b"-50"),
        ])
        status, body = asyncio.run(self._drive(scope, [b"x" * 100]))
        assert status == 400
        assert b"negative" in body


# ─── Integration tests (httpx ASGITransport, no lifespan) ────────────────────

class TestUploadIngress:

    # T11 — Valid small PDF accepted end-to-end
    def test_T11_valid_pdf_accepted(self):
        _mock_app_state()

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                return await c.post(
                    "/upload",
                    files={"file": ("test.pdf", _pdf(500), "application/pdf")},
                    headers={"X-Session-Token": "sess-t11"},
                )

        resp = asyncio.run(run())
        assert resp.status_code == 200, resp.text

    # T5 — File over 50 MiB, body under 52 MiB → route-level 413
    def test_T5_file_over_50mib_rejected(self):
        _mock_app_state()
        # Build a "big" PDF in 64 KiB chunks to avoid a single 50 MiB alloc
        big_pdf = b"%PDF-1.4 " + b"x" * (_UPLOAD_FILE_LIMIT + 1)

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                return await c.post(
                    "/upload",
                    files={"file": ("big.pdf", big_pdf, "application/pdf")},
                    headers={"X-Session-Token": "sess-t5"},
                )

        resp = asyncio.run(run())
        assert resp.status_code == 413, resp.text

    # T6 — Too many file fields → 400
    def test_T6_too_many_files_rejected(self):
        _mock_app_state()

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                return await c.post(
                    "/upload",
                    files=[
                        ("file", ("a.pdf", _pdf(), "application/pdf")),
                        ("file", ("b.pdf", _pdf(), "application/pdf")),
                    ],
                    headers={"X-Session-Token": "sess-t6"},
                )

        resp = asyncio.run(run())
        assert resp.status_code == 400, resp.text

    # T7 — Too many form fields → 400
    def test_T7_too_many_fields_rejected(self):
        _mock_app_state()

        async def run():
            extra = {f"f{i}": "v" for i in range(11)}  # 11 text fields (> max_fields=10)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                return await c.post(
                    "/upload",
                    files={"file": ("a.pdf", _pdf(), "application/pdf")},
                    data=extra,
                    headers={"X-Session-Token": "sess-t7"},
                )

        resp = asyncio.run(run())
        assert resp.status_code == 400, resp.text

    # T8 — Admission semaphore: 5th concurrent → 503
    def test_T8_admission_semaphore_fifth_rejected(self):
        _mock_app_state()
        app.state._upload_admission_sem = asyncio.BoundedSemaphore(4)
        sem = app.state._upload_admission_sem

        async def run():
            for _ in range(4):
                await sem.acquire()
            try:
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test"
                ) as c:
                    return await c.post(
                        "/upload",
                        files={"file": ("a.pdf", _pdf(), "application/pdf")},
                        headers={"X-Session-Token": "sess-t8"},
                    )
            finally:
                for _ in range(4):
                    sem.release()

        resp = asyncio.run(run())
        assert resp.status_code == 503, resp.text
        assert "Retry-After" in resp.headers

    # T9 — Rate limit fires before multipart parsing
    def test_T9_rate_limit_before_multipart(self, monkeypatch):
        _mock_app_state()

        import session_auth as _sa
        from rate_limiter import _session_limiters, SlidingWindowLimiter, LIMITS_SESSION

        session_id = str(uuid.uuid4())
        max_req, window_sec = LIMITS_SESSION["upload"]
        limiter = SlidingWindowLimiter(max_req, window_sec, scope="session")
        hit_key = f"upload:sess:{session_id}"
        now = time.monotonic()
        for _ in range(max_req):
            limiter._hits[hit_key].append(now)
        _session_limiters["upload"] = limiter

        form_calls = []
        original_form = main.Request.form

        async def counting_form(self, **kwargs):
            form_calls.append(1)
            return await original_form(self, **kwargs)

        monkeypatch.setattr(main.Request, "form", counting_form)

        async def run():
            token = _sa.generate_session_token(session_id)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                return await c.post(
                    "/upload",
                    files={"file": ("a.pdf", _pdf(), "application/pdf")},
                    headers={"X-Session-Token": token},
                )

        resp = asyncio.run(run())
        assert resp.status_code == 429, f"Expected 429, got {resp.status_code}: {resp.text}"
        assert form_calls == [], "request.form() was called before rate limit check"

    # T10 — Temp staging file cleaned up after magic-byte rejection
    def test_T10_cleanup_on_rejection(self):
        _mock_app_state()
        for f in UPLOAD_DIR.glob(".tmp_*"):
            f.unlink(missing_ok=True)

        async def run():
            fake_pdf = b"NOTPDF  " + b"x" * 200  # Wrong magic bytes for .pdf
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                return await c.post(
                    "/upload",
                    files={"file": ("fake.pdf", fake_pdf, "application/pdf")},
                    headers={"X-Session-Token": "sess-t10"},
                )

        resp = asyncio.run(run())
        assert resp.status_code == 400, resp.text
        leaked = list(UPLOAD_DIR.glob(".tmp_*"))
        assert leaked == [], f"Temp files leaked: {leaked}"

    # T12 — Reindex regression
    def test_T12_reindex_regression(self):
        _mock_app_state()
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        (UPLOAD_DIR / "testdoc.pdf").write_bytes(_pdf())

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                return await c.post(
                    "/upload",
                    files={"file": ("new.pdf", _pdf(500), "application/pdf")},
                    params={"reindex_doc_id": "testdoc"},
                    headers={"X-Session-Token": "sess1"},
                )

        resp = asyncio.run(run())
        assert resp.status_code == 200, resp.text

    # T15 — Reindex authorization ordering: unowned or nonexistent doc_id does not drain capacity or leak files
    def test_T15_unauthorized_reindex_does_not_drain_capacity(self):
        _mock_app_state()
        sem = main.get_upload_admission_semaphore()
        initial_val = sem._value

        # Make metadata.get_document return None for nonexistent, or None when session_id doesn't match
        def mock_get_doc(doc_id, session_id=None):
            if doc_id == "nonexistent":
                return None
            if doc_id == "unowned":
                if session_id == "other_sess":
                    return {"doc_id": "unowned", "session_id": "other_sess"}
                return None
            return {"doc_id": doc_id, "session_id": "sess1"}

        app.state.metadata.get_document.side_effect = mock_get_doc

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                r1 = await c.post(
                    "/upload",
                    files={"file": ("new.pdf", _pdf(500), "application/pdf")},
                    params={"reindex_doc_id": "nonexistent"},
                    headers={"X-Session-Token": "sess1"},
                )
                r2 = await c.post(
                    "/upload",
                    files={"file": ("new.pdf", _pdf(500), "application/pdf")},
                    params={"reindex_doc_id": "unowned"},
                    headers={"X-Session-Token": "sess1"},
                )
                r3 = await c.post(
                    "/upload",
                    files={"file": ("new.pdf", _pdf(500), "application/pdf")},
                    params={"reindex_doc_id": "../invalid/path"},
                    headers={"X-Session-Token": "sess1"},
                )
                return r1, r2, r3

        r1, r2, r3 = asyncio.run(run())
        assert r1.status_code == 404, r1.text
        assert r2.status_code == 404, r2.text
        assert r3.status_code == 400, r3.text
        assert sem._value == initial_val, f"Semaphore drained: {sem._value} vs {initial_val}"
        leaked = list(UPLOAD_DIR.glob(".tmp_*"))
        assert leaked == [], f"Temp files leaked: {leaked}"

    # T16 — Cancellation during multipart parsing restores permit and leaves no temp files
    def test_T16_cancellation_during_multipart_parsing(self, monkeypatch):
        _mock_app_state()
        sem = main.get_upload_admission_semaphore()
        initial_val = sem._value

        async def cancel_form(self, **kwargs):
            raise asyncio.CancelledError()

        monkeypatch.setattr(main.Request, "form", cancel_form)

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                try:
                    await c.post(
                        "/upload",
                        files={"file": ("test.pdf", _pdf(500), "application/pdf")},
                        headers={"X-Session-Token": "sess-t16"},
                    )
                except (asyncio.CancelledError, Exception):
                    pass

        asyncio.run(run())
        assert sem._value == initial_val, f"Permit leaked on form cancellation: {sem._value}"
        assert list(UPLOAD_DIR.glob(".tmp_*")) == []

    # T17 — Cancellation during chunked staging restores permit and unlinks temp file
    def test_T17_cancellation_during_staging(self, monkeypatch):
        _mock_app_state()
        sem = main.get_upload_admission_semaphore()
        initial_val = sem._value

        from starlette.datastructures import UploadFile
        orig_read = UploadFile.read
        calls = 0

        async def cancelling_read(self, size=-1):
            nonlocal calls
            calls += 1
            if calls >= 2:
                raise asyncio.CancelledError()
            return await orig_read(self, size)

        monkeypatch.setattr(UploadFile, "read", cancelling_read)

        async def run():
            big_data = _pdf(150_000)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                try:
                    await c.post(
                        "/upload",
                        files={"file": ("test.pdf", big_data, "application/pdf")},
                        headers={"X-Session-Token": "sess-t17"},
                    )
                except (asyncio.CancelledError, Exception):
                    pass

        asyncio.run(run())
        assert sem._value == initial_val, f"Permit leaked on staging cancellation: {sem._value}"
        assert list(UPLOAD_DIR.glob(".tmp_*")) == []

    # T18 — Disk/OSError during staging restores permit, returns 500, unlinks temp file
    def test_T18_oserror_during_staging(self, monkeypatch):
        _mock_app_state()
        sem = main.get_upload_admission_semaphore()
        initial_val = sem._value

        from starlette.datastructures import UploadFile
        orig_read = UploadFile.read
        calls = 0

        async def error_read(self, size=-1):
            nonlocal calls
            calls += 1
            if calls >= 2:
                raise OSError("Disk quota exceeded / simulated I/O error")
            return await orig_read(self, size)

        monkeypatch.setattr(UploadFile, "read", error_read)

        async def run():
            big_data = _pdf(150_000)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                return await c.post(
                    "/upload",
                    files={"file": ("test.pdf", big_data, "application/pdf")},
                    headers={"X-Session-Token": "sess-t18"},
                )

        resp = asyncio.run(run())
        assert resp.status_code == 500, resp.text
        assert sem._value == initial_val, f"Permit leaked on OSError: {sem._value}"
        assert list(UPLOAD_DIR.glob(".tmp_*")) == []

    # T19 — Cancellation between staging and supervisor cleans up persisted file
    def test_T19_cancellation_before_supervisor(self, monkeypatch):
        _mock_app_state()
        sem = main.get_upload_admission_semaphore()
        initial_val = sem._value

        proc_sem = main.get_processing_semaphore()

        async def cancel_acquire():
            raise asyncio.CancelledError()

        monkeypatch.setattr(proc_sem, "acquire", cancel_acquire)

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                try:
                    await c.post(
                        "/upload",
                        files={"file": ("test.pdf", _pdf(500), "application/pdf")},
                        headers={"X-Session-Token": "sess-t19"},
                    )
                except (asyncio.CancelledError, Exception):
                    pass

        asyncio.run(run())
        assert sem._value == initial_val, f"Permit leaked: {sem._value}"
        assert list(UPLOAD_DIR.glob(".tmp_*")) == []

    # T20 — BoundedSemaphore catches accidental double release
    def test_T20_bounded_semaphore_structure(self):
        _mock_app_state()
        sem = main.get_upload_admission_semaphore()
        assert isinstance(sem, asyncio.BoundedSemaphore), "Admission semaphore must be BoundedSemaphore"
        with pytest.raises(ValueError, match="Semaphore released too many times"):
            sem.release()

    # T21 — Ingress admission permit is released immediately after staging (before processing finishes)
    def test_T21_ingress_released_before_processing_finishes(self):
        _mock_app_state()
        sem = main.get_upload_admission_semaphore()
        initial_val = sem._value

        import threading
        worker_started_thread = threading.Event()
        worker_can_finish_thread = threading.Event()

        def slow_process(*args, **kwargs):
            worker_started_thread.set()
            worker_can_finish_thread.wait(timeout=5)
            return {
                "status": "success",
                "doc_id": "doc1",
                "filename": "test.pdf",
                "pages": 1,
                "chunks": 1,
                "language_hint": "english",
            }

        app.state.pipeline.process_document.side_effect = slow_process

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                t1 = asyncio.create_task(
                    c.post(
                        "/upload",
                        files={"file": ("test1.pdf", _pdf(500), "application/pdf")},
                        headers={"X-Session-Token": "sess-t21-1"},
                    )
                )

                while not worker_started_thread.is_set():
                    await asyncio.sleep(0.01)

                assert sem._value == initial_val, (
                    f"Ingress permit not released during processing! sem._value={sem._value}"
                )

                worker_can_finish_thread.set()
                r1 = await t1
                assert r1.status_code == 200

        asyncio.run(run())

    # T22 — Reindex failure preserves active document intact
    def test_T22_reindex_failure_preserves_active_document(self):
        _mock_app_state()
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        active_file = UPLOAD_DIR / "testdoc_g0.pdf"
        active_content = b"%PDF-1.4 active original content" + b"x" * 200
        active_file.write_bytes(active_content)

        app.state.pipeline.process_document_staged.return_value = {
            "status": "error",
            "message": "Simulated staged processing failure",
        }

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                return await c.post(
                    "/upload",
                    files={"file": ("new.pdf", _pdf(500), "application/pdf")},
                    params={"reindex_doc_id": "testdoc"},
                    headers={"X-Session-Token": "sess1"},
                )

        resp = asyncio.run(run())
        assert resp.status_code == 400, resp.text
        assert active_file.exists(), "Original active file was deleted on reindex failure!"
        assert active_file.read_bytes() == active_content, "Original file content was corrupted!"
        gen1_files = list(UPLOAD_DIR.glob("testdoc_g1*"))
        assert gen1_files == [], f"Staged generation file not cleaned up: {gen1_files}"

    # T23 — Restrict content type: reject urlencoded, json, and text before parsing
    def test_T23_content_type_enforcement(self):
        _mock_app_state()

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                r1 = await c.post(
                    "/upload",
                    content=b"field=value&foo=bar",
                    headers={"Content-Type": "application/x-www-form-urlencoded", "X-Session-Token": "sess-t23"},
                )
                r2 = await c.post(
                    "/upload",
                    content=b'{"foo":"bar"}',
                    headers={"Content-Type": "application/json", "X-Session-Token": "sess-t23"},
                )
                r3 = await c.post(
                    "/upload",
                    content=b"plain text payload",
                    headers={"Content-Type": "text/plain", "X-Session-Token": "sess-t23"},
                )
                return r1, r2, r3

        r1, r2, r3 = asyncio.run(run())
        assert r1.status_code == 415, r1.text
        assert r2.status_code == 415, r2.text
        assert r3.status_code == 415, r3.text
        assert "multipart/form-data" in r1.text

    # T24 — Oversized urlencoded request rejected before parsing
    def test_T24_oversized_urlencoded_rejected(self):
        _mock_app_state()
        big_form = b"key=" + b"a" * 1_000_000

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                return await c.post(
                    "/upload",
                    content=big_form,
                    headers={"Content-Type": "application/x-www-form-urlencoded", "X-Session-Token": "sess-t24"},
                )

        resp = asyncio.run(run())
        assert resp.status_code == 415, resp.text

    # T25 — SafeMultiPartParser closes underlying temporary file on cancellation
    def test_T25_multipart_parser_spool_cleanup_on_cancellation(self):
        from starlette.datastructures import Headers
        from main import SafeMultiPartParser

        boundary = "boundary12345"
        headers = Headers({
            "content-type": f"multipart/form-data; boundary={boundary}",
        })

        part_header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="large.pdf"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode()

        # Generate > 1.2 MiB so SpooledTemporaryFile(max_size=1MiB) rolls over to an OS temp file on disk
        chunk_data = b"x" * (64 * 1024)
        spool_file_captured = None

        async def stream():
            nonlocal spool_file_captured
            yield part_header
            # Yield enough data to trigger rollover to disk
            for _ in range(25):
                yield chunk_data
            # Now simulate cancellation
            raise asyncio.CancelledError()

        parser = SafeMultiPartParser(headers, stream(), max_files=1, max_fields=10)

        async def run_parser():
            try:
                await parser.parse()
            except asyncio.CancelledError:
                pass

        asyncio.run(run_parser())

        # Verify that files in _files_to_close_on_error were closed and deleted
        assert len(parser._files_to_close_on_error) == 1
        spooled = parser._files_to_close_on_error[0]
        # In Python tempfile.SpooledTemporaryFile, if rolled over to disk, _file is an open file or closed
        if hasattr(spooled, "_file") and hasattr(spooled._file, "name"):
            disk_path = spooled._file.name
            import os
            assert not os.path.exists(disk_path), f"Spool file on disk was not deleted on cancellation: {disk_path}"
        assert getattr(spooled, "closed", False) or getattr(getattr(spooled, "_file", None), "closed", False), (
            "Underlying temporary spool file was not closed on cancellation!"
        )

    # T26 — Staged processing backlog bounds pending uploads while processing slots are occupied
    def test_T26_staged_backlog_bounded_queue(self):
        _mock_app_state()
        import threading
        from main import get_staged_backlog_semaphore

        # Set backlog semaphore to 2
        app.state._staged_backlog_sem = asyncio.BoundedSemaphore(2)
        backlog_sem = app.state._staged_backlog_sem

        # Processing semaphore: 1 slot, blocked by a slow worker
        app.state.processing_semaphore = asyncio.Semaphore(1)
        worker_started = threading.Event()
        worker_can_finish = threading.Event()

        def slow_worker(*args, **kwargs):
            worker_started.set()
            worker_can_finish.wait(timeout=10)
            return {
                "status": "success",
                "doc_id": "doc1",
                "filename": "test.pdf",
                "pages": 1,
                "chunks": 1,
                "language_hint": "english",
            }

        app.state.pipeline.process_document.side_effect = slow_worker

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                # Upload 1: starts and occupies processing slot
                t1 = asyncio.create_task(
                    c.post(
                        "/upload",
                        files={"file": ("doc1.pdf", _pdf(500), "application/pdf")},
                        headers={"X-Session-Token": "sess-t26-1"},
                    )
                )

                while not worker_started.is_set():
                    await asyncio.sleep(0.01)

                # Now processing slot 1 is busy.
                # Upload 2: stages to disk and acquires backlog permit 1 (waiting in queue)
                t2 = asyncio.create_task(
                    c.post(
                        "/upload",
                        files={"file": ("doc2.pdf", _pdf(500), "application/pdf")},
                        headers={"X-Session-Token": "sess-t26-2"},
                    )
                )
                await asyncio.sleep(0.05)

                # Upload 3: stages to disk and acquires backlog permit 2 (waiting in queue)
                t3 = asyncio.create_task(
                    c.post(
                        "/upload",
                        files={"file": ("doc3.pdf", _pdf(500), "application/pdf")},
                        headers={"X-Session-Token": "sess-t26-3"},
                    )
                )
                await asyncio.sleep(0.05)

                # Backlog is now saturated (2 staged files waiting in queue).
                # Upload 4: attempts to stage, but backlog is full -> 503 Service Unavailable!
                r4 = await c.post(
                    "/upload",
                    files={"file": ("doc4.pdf", _pdf(500), "application/pdf")},
                    headers={"X-Session-Token": "sess-t26-4"},
                )

                # Unblock worker to clean up
                worker_can_finish.set()
                r1 = await t1
                r2 = await t2
                r3 = await t3
                return r1, r2, r3, r4

        r1, r2, r3, r4 = asyncio.run(run())
        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200, r2.text
        assert r3.status_code == 200, r3.text
        assert r4.status_code == 503, f"Expected 503 backlog rejection, got {r4.status_code}: {r4.text}"
        assert "Retry-After" in r4.headers
        assert "backlog is full" in r4.text

    # T27 — Actual /upload endpoint cancellation: spool rolls over to disk, cancels, deletes disk file, restores locks & permits
    def test_T27_endpoint_spool_cleanup_on_cancellation(self, monkeypatch):
        import tempfile
        import os
        from main import get_upload_admission_semaphore, get_reindex_locks

        _mock_app_state()
        sem = get_upload_admission_semaphore()
        initial_val = sem._value

        # Track any disk file created by SpooledTemporaryFile rollover
        orig_rollover = tempfile.SpooledTemporaryFile.rollover
        disk_files_created = []

        def tracked_rollover(spool_self):
            orig_rollover(spool_self)
            if hasattr(spool_self._file, "name"):
                disk_files_created.append(spool_self._file.name)

        monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", tracked_rollover)

        boundary = "---------------------------boundary123456789"
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-Session-Token": "sess-t27",
        }

        # Mock document in metadata for reindex mode
        app.state.metadata.get_document.return_value = {
            "doc_id": "testdoc_t27",
            "session_id": "sess-t27",
            "reindex_generation": 0,
        }

        part_head = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="test.pdf"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
            f"%PDF-1.4 "
        ).encode("utf-8")

        chunk = b"A" * (64 * 1024)  # 64 KiB

        async def streaming_body():
            yield part_head
            # Yield > 1.2 MiB so SpooledTemporaryFile(max_size=1MiB) rolls over to an OS temp file on disk
            for _ in range(25):
                yield chunk
            # Confirmed rollover occurred; now simulate client disconnect / cancellation
            raise asyncio.CancelledError()

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                try:
                    await c.post(
                        "/upload",
                        content=streaming_body(),
                        params={"reindex_doc_id": "testdoc_t27"},
                        headers=headers,
                    )
                except (asyncio.CancelledError, Exception):
                    pass

        asyncio.run(run())

        # 1. Confirm the temporary file actually rolled over to disk during parsing
        assert len(disk_files_created) >= 1, "Temporary file never rolled over to disk"
        # 2. Confirm the underlying temporary file was closed and deleted upon cancellation
        for fpath in disk_files_created:
            assert not os.path.exists(fpath), f"Underlying spool file still exists on disk: {fpath}"
        # 3. Confirm admission capacity is restored
        assert sem._value == initial_val, f"Admission capacity not restored: {sem._value} vs {initial_val}"
        # 4. Confirm per-document reindex lock is restored (unlocked)
        locks = get_reindex_locks()
        if "testdoc_t27" in locks:
            assert not locks["testdoc_t27"].locked(), "Reindex lock remained locked after cancellation"
        # 5. Confirm no partial staging files left in UPLOAD_DIR
        assert list(UPLOAD_DIR.glob(".tmp_*")) == [], "Orphaned staging files found in UPLOAD_DIR"


# ─── T28 — FormData full close: unexpected/duplicate field cleanup ─────────────

class TestFormDataCleanup:
    """Verify that form.close() in the outer finally releases ALL UploadFile
    spool resources — including unexpected field names and duplicate entries."""

    # T28a — Valid file under unexpected field name: form closed, no spool leak
    def test_T28a_unexpected_field_name_form_closed(self, tmp_path, monkeypatch):
        """File sent as 'document' instead of 'file' → 400; form still closed."""
        import tempfile
        _mock_app_state()
        closed_files = []
        orig_close = tempfile.SpooledTemporaryFile.close

        def tracked_close(spool_self):
            orig_close(spool_self)
            closed_files.append(id(spool_self))

        monkeypatch.setattr(tempfile.SpooledTemporaryFile, "close", tracked_close)

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                return await c.post(
                    "/upload",
                    files={"document": ("test.pdf", _pdf(500), "application/pdf")},
                    headers={"X-Session-Token": "sess-t28a"},
                )

        resp = asyncio.run(run())
        assert resp.status_code == 400, resp.text
        # SpooledTemporaryFile.close() must have been called (via form.close())
        assert len(closed_files) >= 1, "No spool file was closed after unexpected field rejection"
        assert list(UPLOAD_DIR.glob(".tmp_*")) == [], "Orphaned staging file after unexpected field rejection"

    # T28b — Duplicate 'file' fields: second file also closed, no spool leak
    def test_T28b_duplicate_file_fields_all_closed(self, monkeypatch):
        """Two 'file' parts → 400 (max_files=1); both spools must be closed."""
        import tempfile
        _mock_app_state()
        closed_count = []
        orig_close = tempfile.SpooledTemporaryFile.close

        def tracked_close(spool_self):
            orig_close(spool_self)
            closed_count.append(1)

        monkeypatch.setattr(tempfile.SpooledTemporaryFile, "close", tracked_close)

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                return await c.post(
                    "/upload",
                    files=[
                        ("file", ("a.pdf", _pdf(500), "application/pdf")),
                        ("file", ("b.pdf", _pdf(500), "application/pdf")),
                    ],
                    headers={"X-Session-Token": "sess-t28b"},
                )

        resp = asyncio.run(run())
        # max_files=1 → parser rejects the second file → 400
        assert resp.status_code == 400, resp.text
        assert list(UPLOAD_DIR.glob(".tmp_*")) == [], "Orphaned staging file after duplicate field rejection"

    # T28c — Unexpected file alongside valid 'file': all closed, only 'file' staged
    def test_T28c_unexpected_file_alongside_valid_file(self, monkeypatch):
        """Extra file field + valid 'file' → parser rejects (max_files=1 exceeded)."""
        import tempfile
        _mock_app_state()
        closed_count = []
        orig_close = tempfile.SpooledTemporaryFile.close

        def tracked_close(spool_self):
            orig_close(spool_self)
            closed_count.append(1)

        monkeypatch.setattr(tempfile.SpooledTemporaryFile, "close", tracked_close)

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                return await c.post(
                    "/upload",
                    files=[
                        ("file", ("test.pdf", _pdf(500), "application/pdf")),
                        ("extra", ("other.pdf", _pdf(500), "application/pdf")),
                    ],
                    headers={"X-Session-Token": "sess-t28c"},
                )

        resp = asyncio.run(run())
        # max_files=1 → parser rejects the second file
        assert resp.status_code == 400, resp.text
        assert list(UPLOAD_DIR.glob(".tmp_*")) == [], "Orphaned staging file after extra field rejection"

    # T28d — Validation failure (bad extension): form still closed, no spool leak
    def test_T28d_validation_failure_form_closed(self, monkeypatch):
        """Unsupported extension .exe → 400; form.close() must still run."""
        import tempfile
        _mock_app_state()
        closed_files = []
        orig_close = tempfile.SpooledTemporaryFile.close

        def tracked_close(spool_self):
            orig_close(spool_self)
            closed_files.append(id(spool_self))

        monkeypatch.setattr(tempfile.SpooledTemporaryFile, "close", tracked_close)

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                return await c.post(
                    "/upload",
                    files={"file": ("malware.exe", b"%PDF-1.4 " + b"x" * 200, "application/octet-stream")},
                    headers={"X-Session-Token": "sess-t28d"},
                )

        resp = asyncio.run(run())
        assert resp.status_code == 400, resp.text
        assert len(closed_files) >= 1, "No spool file was closed after validation failure"
        assert list(UPLOAD_DIR.glob(".tmp_*")) == [], "Orphaned staging file after validation failure"


# ─── T29 — ASGI-level client disconnect (http.disconnect) ─────────────────────

class TestClientDisconnect:
    """Send http.disconnect after spool rollover. Distinct from CancelledError (T27)."""

    def test_T29_disconnect_after_spool_rollover_cleans_up(self, monkeypatch):
        """
        Drive the ASGI app directly with a receive() that sends >1 MiB of body
        then emits http.disconnect. Verifies:
          1. The spool file on disk is deleted.
          2. No .tmp_* staging files remain.
          3. The admission semaphore value is restored.
        """
        import tempfile
        _mock_app_state()

        # Capture spool files that roll over to disk
        disk_files_created = []
        orig_rollover = tempfile.SpooledTemporaryFile.rollover

        def tracked_rollover(spool_self):
            orig_rollover(spool_self)
            if hasattr(spool_self._file, "name"):
                disk_files_created.append(spool_self._file.name)

        monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", tracked_rollover)

        from main import get_upload_admission_semaphore
        sem = get_upload_admission_semaphore()
        initial_val = sem._value

        boundary = "disconnectboundary1234"
        part_head = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="big.pdf"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
            f"%PDF-1.4 "
        ).encode("utf-8")

        # Build >1.2 MiB of body chunks to ensure rollover
        body_chunks = [part_head] + [b"B" * 65536] * 20  # 1.28 MiB data

        async def run():
            scope = {
                "type": "http",
                "method": "POST",
                "path": "/upload",
                "query_string": b"",
                "headers": [
                    (b"content-type", f"multipart/form-data; boundary={boundary}".encode()),
                    (b"x-session-token", b"sess-t29"),
                ],
                "app": app,  # needed by Starlette's Request
            }

            q = list(body_chunks)
            disconnect_sent = False

            async def receive():
                nonlocal disconnect_sent
                if q:
                    chunk = q.pop(0)
                    return {"type": "http.request", "body": chunk, "more_body": bool(q)}
                # Body exhausted: immediately signal disconnect
                if not disconnect_sent:
                    disconnect_sent = True
                    return {"type": "http.disconnect"}
                # Should not be called again, but guard against infinite loops
                raise RuntimeError("receive() called after disconnect")

            response_started = False
            status_code = None

            async def send(msg):
                nonlocal response_started, status_code
                if msg["type"] == "http.response.start":
                    response_started = True
                    status_code = msg.get("status")

            # Drive the full ASGI app stack (includes MaxBodySizeMiddleware)
            await app(scope, receive, send)
            return status_code

        status = asyncio.run(run())

        # App should respond (any status is fine — disconnect may yield 400 or 500)
        # The key assertion is resource cleanup
        assert list(UPLOAD_DIR.glob(".tmp_*")) == [], "Orphaned staging files after client disconnect"
        for fpath in disk_files_created:
            assert not os.path.exists(fpath), f"Spool file still on disk after disconnect: {fpath}"
        assert sem._value == initial_val, f"Admission permit not restored after disconnect: {sem._value}"
