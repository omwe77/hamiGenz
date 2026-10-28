"""
Tests for event-loop thread offloading, worker lifecycle, cooperative deadline
enforcement, and concurrency control (Task 2.1.1-R1).

Verifies:
1. Normal event-loop responsiveness: lightweight requests (/health) are not starved
   by synchronous pipeline execution.
2. Normal concurrency limiting: semaphore strictly bounds simultaneous execution.
3. Queue timeout: requests that time out waiting for the processing queue abort
   before starting a worker and do not leak permits.
4. Worker lifecycle: processing permit remains occupied until the worker thread
   actually reaches its terminal state, even if a processing deadline is exceeded.
5. No premature third request: a subsequent request cannot start while a timed-out
   worker is still active.
6. No ghost commitment: timeouts before the persistence stage commit zero vectors,
   metadata, or chunk records.
7. Safe file cleanup: the uploaded input file is never deleted while the worker is
   still executing and is cleaned up only after the worker reaches a safe terminal state.
8. Persistence-boundary consistency: once persistence starts, it finishes completely
   and reports success, or rolls back atomically on failure. Never returns 503
   followed by a background commit.
"""

import os
import sys
import time
import asyncio
import threading
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import httpx

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import main
from main import app, get_processing_semaphore
from vector_store import Pipeline, VectorStore, EmbeddingService, ProcessingTimeoutError
from document_processor import Chunker, MetadataStore


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset in-memory rate limiters between tests to prevent IP ceiling saturation."""
    from rate_limiter import _ip_limiters, _session_limiters
    _ip_limiters.clear()
    _session_limiters.clear()


@pytest.fixture
def mock_pipeline():
    """Ensure app.state.pipeline exists for testing upload_document."""
    mock_p = MagicMock()
    mock_p.process_document.return_value = {
        "status": "success",
        "doc_id": "test_doc_01",
        "filename": "test.pdf",
        "pages": 1,
        "chunks": 2,
        "language_hint": "english",
    }
    app.state.pipeline = mock_p
    app.state.vector_store = MagicMock()
    app.state.metadata = MagicMock()
    app.state.metadata.get_document.return_value = None
    app.state.metadata.list_documents.return_value = []
    return mock_p


# ─── 1. Event Loop Responsiveness ─────────────────────────────────────────

def test_event_loop_not_blocked_during_upload(mock_pipeline):
    """
    Prove that slow synchronous document processing does not block the main
    event loop: concurrent /health requests respond in < 250ms.
    """
    async def _run():
        worker_started = threading.Event()

        def slow_process(*args, **kwargs):
            worker_started.set()
            time.sleep(0.35)
            return {
                "status": "success",
                "doc_id": "slow_doc",
                "filename": "test.pdf",
                "pages": 1,
                "chunks": 1,
                "language_hint": "english",
            }

        mock_pipeline.process_document.side_effect = slow_process
        valid_pdf_bytes = b"%PDF-1.4\n" + b"0" * 200

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            upload_task = asyncio.create_task(
                client.post(
                    "/upload",
                    files={"file": ("test.pdf", valid_pdf_bytes, "application/pdf")},
                )
            )

            # Wait deterministically until the worker thread has started
            for _ in range(100):
                if worker_started.is_set():
                    break
                await asyncio.sleep(0.005)

            # Probe /health while worker thread is active
            start_probe = time.perf_counter()
            health_resp = await client.get("/health")
            probe_elapsed = time.perf_counter() - start_probe

            assert health_resp.status_code == 200
            assert probe_elapsed < 0.25, f"/health took {probe_elapsed:.3f}s — event loop was blocked!"

            upload_resp = await upload_task
            assert upload_resp.status_code == 200
            assert bool(upload_resp.json()["doc_id"])

    asyncio.run(_run())


# ─── 2. Normal Concurrency Capacity ───────────────────────────────────────

def test_concurrency_semaphore_limits_parallel_processing(mock_pipeline):
    """
    Verify that the concurrency semaphore strictly bounds parallel execution
    inside process_document to the configured capacity.
    """
    async def _run():
        with patch.object(main, "get_processing_semaphore") as mock_get_sem:
            test_sem = asyncio.Semaphore(1)
            mock_get_sem.return_value = test_sem

            active_processing = 0
            max_seen_active = 0
            lock = threading.Lock()

            def tracked_process(*args, **kwargs):
                nonlocal active_processing, max_seen_active
                with lock:
                    active_processing += 1
                    if active_processing > max_seen_active:
                        max_seen_active = active_processing
                time.sleep(0.1)
                with lock:
                    active_processing -= 1
                return {
                    "status": "success",
                    "doc_id": "test_doc",
                    "filename": "test.pdf",
                    "pages": 1,
                    "chunks": 1,
                    "language_hint": "english",
                }

            mock_pipeline.process_document.side_effect = tracked_process
            valid_pdf_bytes = b"%PDF-1.4\n" + b"0" * 200

            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                t1 = client.post("/upload", files={"file": ("test1.pdf", valid_pdf_bytes, "application/pdf")})
                t2 = client.post("/upload", files={"file": ("test2.pdf", valid_pdf_bytes, "application/pdf")})

                resps = await asyncio.gather(t1, t2)
                for r in resps:
                    assert r.status_code == 200

                assert max_seen_active == 1

    asyncio.run(_run())


# ─── 3. Queue Timeout Without Permit Leak ─────────────────────────────────

def test_queue_timeout_starts_no_worker_and_does_not_leak_permit(mock_pipeline):
    """
    Prove that a request timing out while waiting for a semaphore permit:
    1. Returns HTTP 503 ("Server busy processing documents").
    2. Never starts a worker (process_document is not invoked).
    3. Does not leak permits (semaphore returns to expected capacity).
    """
    async def _run():
        test_sem = asyncio.Semaphore(1)
        # Pre-acquire the semaphore to simulate a fully saturated queue
        await test_sem.acquire()
        assert test_sem.locked()

        valid_pdf_bytes = b"%PDF-1.4\n" + b"0" * 200

        with patch.object(main, "get_processing_semaphore", return_value=test_sem):
            with patch.dict(os.environ, {"HAMIGENZ_QUEUE_TIMEOUT_SECONDS": "0.05"}):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                    resp = await client.post(
                        "/upload",
                        files={"file": ("test.pdf", valid_pdf_bytes, "application/pdf")},
                    )

                    assert resp.status_code == 503
                    assert "Server busy processing documents" in resp.json()["detail"]
                    mock_pipeline.process_document.assert_not_called()

        # Release the pre-acquired hold: verify no permit leak occurred
        test_sem.release()
        assert not test_sem.locked()
        assert test_sem._value == 1

    asyncio.run(_run())


# ─── 4. Worker Lifecycle & Semaphore Retention on Timeout ─────────────────

def test_worker_lifecycle_permit_occupied_until_thread_exits(mock_pipeline):
    """
    Prove that when a processing deadline is exceeded, the semaphore permit
    REMAINS OCCUPIED for the full duration of the worker thread's execution,
    and is only released after the worker has completely returned and cleaned up.
    """
    async def _run():
        test_sem = asyncio.Semaphore(1)
        worker_reached_check = threading.Event()
        allow_worker_exit = threading.Event()

        def timing_out_worker(*args, **kwargs):
            worker_reached_check.set()
            # Worker is blocked in a synchronous stage
            allow_worker_exit.wait(timeout=5.0)
            raise ProcessingTimeoutError("Processing deadline exceeded")

        mock_pipeline.process_document.side_effect = timing_out_worker
        valid_pdf_bytes = b"%PDF-1.4\n" + b"0" * 200

        with patch.object(main, "get_processing_semaphore", return_value=test_sem):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                upload_task = asyncio.create_task(
                    client.post(
                        "/upload",
                        files={"file": ("test.pdf", valid_pdf_bytes, "application/pdf")},
                    )
                )

                # Wait until the worker thread has acquired the permit and is executing
                for _ in range(200):
                    if worker_reached_check.is_set():
                        break
                    await asyncio.sleep(0.01)
                assert worker_reached_check.is_set(), "Worker thread did not start in time"

                # CRITICAL INVARIANT: The permit must still be occupied while worker is inside
                assert test_sem.locked(), "Permit was prematurely released while worker thread was active!"
                assert test_sem._value == 0

                # Release the worker thread to allow it to raise ProcessingTimeoutError and exit
                allow_worker_exit.set()

                resp = await upload_task
                assert resp.status_code == 503
                assert "Document processing timed out" in resp.json()["detail"]

                # Now that worker has completely finished, permit is released
                assert not test_sem.locked()
                assert test_sem._value == 1

    asyncio.run(_run())


# ─── 5. No Premature Third Request ────────────────────────────────────────

def test_no_premature_third_request_during_delayed_worker_exit(mock_pipeline):
    """
    With semaphore capacity one, prove that a third request cannot begin processing
    while the first worker continues executing after its deadline.
    """
    async def _run():
        test_sem = asyncio.Semaphore(1)
        worker1_in_stage = threading.Event()
        allow_worker1_exit = threading.Event()
        order_of_entry = []
        lock = threading.Lock()

        def worker_func(filepath, doc_id, filename, *args, **kwargs):
            with lock:
                order_of_entry.append(filename)
            if filename == "doc1.pdf":
                worker1_in_stage.set()
                allow_worker1_exit.wait(timeout=5.0)
                raise ProcessingTimeoutError("Doc 1 timed out")
            return {
                "status": "success",
                "doc_id": doc_id,
                "filename": filename,
                "pages": 1,
                "chunks": 1,
                "language_hint": "english",
            }

        mock_pipeline.process_document.side_effect = worker_func
        valid_pdf_bytes = b"%PDF-1.4\n" + b"0" * 200

        with patch.object(main, "get_processing_semaphore", return_value=test_sem):
            # Large queue timeout so requests queue cleanly
            with patch.dict(os.environ, {"HAMIGENZ_QUEUE_TIMEOUT_SECONDS": "5.0"}):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                    t1 = asyncio.create_task(
                        client.post("/upload", files={"file": ("doc1.pdf", valid_pdf_bytes, "application/pdf")})
                    )
                    for _ in range(200):
                        if worker1_in_stage.is_set():
                            break
                        await asyncio.sleep(0.01)
                    assert worker1_in_stage.is_set(), "Worker 1 did not reach stage in time"

                    # Start doc2 while worker1 is still blocked in its thread
                    t2 = asyncio.create_task(
                        client.post("/upload", files={"file": ("doc2.pdf", valid_pdf_bytes, "application/pdf")})
                    )
                    # Start doc3
                    t3 = asyncio.create_task(
                        client.post("/upload", files={"file": ("doc3.pdf", valid_pdf_bytes, "application/pdf")})
                    )

                    await asyncio.sleep(0.05)

                    # While worker1 is blocked, neither doc2 nor doc3 must have entered process_document
                    with lock:
                        assert order_of_entry == ["doc1.pdf"], f"Premature entry detected: {order_of_entry}"

                    # Unblock worker1
                    allow_worker1_exit.set()

                    r1 = await t1
                    r2 = await t2
                    r3 = await t3

                    assert r1.status_code == 503
                    assert r2.status_code == 200
                    assert r3.status_code == 200

                    with lock:
                        # Sequential execution guaranteed
                        assert order_of_entry == ["doc1.pdf", "doc2.pdf", "doc3.pdf"]

    asyncio.run(_run())


# ─── 6. No Ghost Commitment on Timeout ────────────────────────────────────

def test_no_ghost_commitment_on_timeout():
    """
    Trigger a deadline timeout before persistence on a real Pipeline instance.
    Verify that zero vector files, registry entries, or SQLite records are committed.
    """
    tmp_dir = tempfile.mkdtemp(prefix="hamigenz_ghost_test_")
    try:
        vectors_dir = os.path.join(tmp_dir, "vectors")
        db_path = os.path.join(tmp_dir, "test.db")
        upload_path = os.path.join(tmp_dir, "test.txt")

        # Create dummy text document
        with open(upload_path, "w", encoding="utf-8") as f:
            f.write("Line one of test document content.\n" * 10)

        # Mock embedding service to avoid loading heavyweight neural weights
        embedder = MagicMock()
        embedder.dimension = 384
        import numpy as np
        embedder.embed_texts.return_value = np.zeros((2, 384), dtype=np.float32)

        vstore = VectorStore(vectors_dir=vectors_dir, dimension=384)
        chunker = Chunker(chunk_size=100, overlap=10)
        metadata = MetadataStore(db_path=db_path)

        pipeline = Pipeline(
            embedding_service=embedder,
            vector_store=vstore,
            chunker=chunker,
            metadata_store=metadata,
        )

        doc_id = "ghost_doc_001"
        # Set deadline to a time in the past to trigger immediate timeout before persistence
        past_deadline = time.monotonic() - 1.0

        with pytest.raises(ProcessingTimeoutError) as exc_info:
            pipeline.process_document(
                filepath=upload_path,
                doc_id=doc_id,
                filename="test.txt",
                session_id="session_ghost",
                deadline=past_deadline,
            )

        assert "deadline exceeded" in str(exc_info.value).lower()

        # Invariant 1: No FAISS index or meta file exists on disk
        faiss_file = os.path.join(vectors_dir, f"{doc_id}.faiss")
        meta_file = os.path.join(vectors_dir, f"{doc_id}_meta.json")
        assert not os.path.exists(faiss_file), "Ghost FAISS index was created on disk!"
        assert not os.path.exists(meta_file), "Ghost vector metadata was created on disk!"

        # Invariant 2: Doc id not in vector store registry
        assert doc_id not in vstore._doc_indices

        # Invariant 3: No rows in SQLite documents or chunks tables
        assert metadata.get_document(doc_id, session_id="session_ghost") is None
        conn = metadata._get_connection()
        chunk_count = conn.execute("SELECT count(*) FROM chunks WHERE doc_id=?", (doc_id,)).fetchone()[0]
        conn.close()
        assert chunk_count == 0, "Ghost chunks were committed to SQLite!"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─── 7. Safe File Cleanup After Worker Reaches Terminal State ──────────────

def test_safe_file_cleanup_only_after_worker_terminal_state(mock_pipeline):
    """
    Prove that the uploaded file remains present on disk while the worker
    is using it, and is unlinked only after the worker has reached its terminal state.
    """
    async def _run():
        worker_reading_file = threading.Event()
        allow_worker_finish = threading.Event()
        observed_file_present_during_work = None
        saved_filepath = None

        def worker_inspects_file(filepath, *args, **kwargs):
            nonlocal observed_file_present_during_work, saved_filepath
            saved_filepath = filepath
            # Verify file exists on disk while worker is actively running
            observed_file_present_during_work = os.path.exists(filepath)
            worker_reading_file.set()
            allow_worker_finish.wait(timeout=5.0)
            raise ProcessingTimeoutError("Timed out after inspection")

        mock_pipeline.process_document.side_effect = worker_inspects_file
        valid_pdf_bytes = b"%PDF-1.4\n" + b"0" * 200

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            upload_task = asyncio.create_task(
                client.post("/upload", files={"file": ("sample.pdf", valid_pdf_bytes, "application/pdf")})
            )

            # Wait until worker is actively inspecting the file
            for _ in range(200):
                if worker_reading_file.is_set():
                    break
                await asyncio.sleep(0.01)
            assert worker_reading_file.is_set(), "Worker did not reach inspection in time"
            assert observed_file_present_during_work is True

            # Allow worker to finish with ProcessingTimeoutError
            allow_worker_finish.set()

            resp = await upload_task
            assert resp.status_code == 503

            # Verify the uploaded file has been cleaned up safely
            assert saved_filepath is not None
            assert not os.path.exists(saved_filepath), f"Upload file {saved_filepath} was not cleaned up after terminal state!"

    asyncio.run(_run())


# ─── 8. Persistence Boundary Consistency ──────────────────────────────────

def test_persistence_boundary_consistency():
    """
    Verify that if the deadline check before persistence passes, the storage
    stage executes to completion and is reported as successful, never returning
    a 503 followed by background state commitment.
    """
    import fitz
    tmp_dir = tempfile.mkdtemp(prefix="hamigenz_persist_test_")
    try:
        vectors_dir = os.path.join(tmp_dir, "vectors")
        db_path = os.path.join(tmp_dir, "test.db")
        upload_path = os.path.join(tmp_dir, "test.pdf")

        # Create valid PDF with text
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 72), "Meaningful chunk text line for testing persistence.\n" * 5)
        doc.save(upload_path)
        doc.close()

        embedder = MagicMock()
        embedder.dimension = 384
        import numpy as np
        embedder.embed_texts.return_value = np.zeros((1, 384), dtype=np.float32)

        vstore = VectorStore(vectors_dir=vectors_dir, dimension=384)
        chunker = Chunker(chunk_size=500, overlap=10)
        metadata = MetadataStore(db_path=db_path)

        pipeline = Pipeline(
            embedding_service=embedder,
            vector_store=vstore,
            chunker=chunker,
            metadata_store=metadata,
        )

        doc_id = "doc_persist_ok"
        # Ample deadline (10 seconds) ensuring deadline check before persistence passes
        generous_deadline = time.monotonic() + 10.0

        res = pipeline.process_document(
            filepath=upload_path,
            doc_id=doc_id,
            filename="test.pdf",
            session_id="session_ok",
            deadline=generous_deadline,
        )

        assert res["status"] == "success"
        assert res["chunks"] >= 1

        # Both vector store and metadata must be fully and consistently committed
        assert doc_id in vstore._doc_indices
        assert os.path.exists(os.path.join(vectors_dir, f"{doc_id}.faiss"))
        assert metadata.get_document(doc_id, session_id="session_ok") is not None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─── 9. Cancellation-Safe Worker Supervision (Task 2.1.1-R2) ──────────────

def test_cancellation_safe_worker_supervision(mock_pipeline):
    """
    Regression test for Task 2.1.1-R2:
    Starts a worker, cancels the request coroutine while the worker is blocked, and proves:
    - The worker remains active until explicitly released.
    - The processing permit is not released prematurely.
    - Another request cannot enter the protected processing stage before the original worker exits.
    - Cleanup occurs only when safe, with storage outcome handled consistently.
    """
    async def _run():
        test_sem = asyncio.Semaphore(1)
        worker1_started = threading.Event()
        worker1_blocked = threading.Event()
        worker1_finished = threading.Event()
        worker2_started = threading.Event()

        def worker1_func(filepath, doc_id, filename, *args, **kwargs):
            worker1_started.set()
            worker1_blocked.wait(timeout=5.0)
            worker1_finished.set()
            return {
                "status": "success",
                "doc_id": doc_id,
                "filename": filename,
                "pages": 1,
                "chunks": 1,
                "language_hint": "english",
            }

        def worker2_func(filepath, doc_id, filename, *args, **kwargs):
            worker2_started.set()
            return {
                "status": "success",
                "doc_id": doc_id,
                "filename": filename,
                "pages": 1,
                "chunks": 1,
                "language_hint": "english",
            }

        call_count = 0
        def dispatch_process(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return worker1_func(*args, **kwargs)
            return worker2_func(*args, **kwargs)

        mock_pipeline.process_document.side_effect = dispatch_process
        valid_pdf_bytes = b"%PDF-1.4\n" + b"0" * 200

        with patch.object(main, "get_processing_semaphore", return_value=test_sem):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                req1_task = asyncio.create_task(
                    client.post("/upload", files={"file": ("doc1.pdf", valid_pdf_bytes, "application/pdf")})
                )

                # Wait until worker 1 starts executing in its thread
                for _ in range(200):
                    if worker1_started.is_set():
                        break
                    await asyncio.sleep(0.01)
                assert worker1_started.is_set(), "Worker 1 did not start in time"

                # Cancel request 1 coroutine while worker 1 is blocked
                req1_task.cancel()
                try:
                    await req1_task
                except (asyncio.CancelledError, httpx.RequestError):
                    pass

                # Invariant 1: Worker 1 remains active
                assert not worker1_finished.is_set(), "Worker 1 terminated prematurely upon coroutine cancellation!"

                # Invariant 2: Processing permit remains occupied
                assert test_sem.locked(), "Processing permit was released prematurely while worker 1 was active!"
                assert test_sem._value == 0

                # Invariant 3: Request 2 cannot enter processing stage while worker 1 is still running
                req2_task = asyncio.create_task(
                    client.post("/upload", files={"file": ("doc2.pdf", valid_pdf_bytes, "application/pdf")})
                )
                await asyncio.sleep(0.05)
                assert not worker2_started.is_set(), "Worker 2 entered processing before worker 1 finished!"

                # Invariant 4: Explicitly unblock worker 1
                worker1_blocked.set()
                for _ in range(200):
                    if worker1_finished.is_set():
                        break
                    await asyncio.sleep(0.01)
                assert worker1_finished.is_set(), "Worker 1 did not complete after being unblocked"

                # Request 2 now enters and finishes cleanly
                resp2 = await req2_task
                assert resp2.status_code == 200
                assert worker2_started.is_set()

                # Permit is completely released back to 1
                assert not test_sem.locked()
                assert test_sem._value == 1

    asyncio.run(_run())


# ─── 10. Deadline Expiry During Embedding (Task 2.1.1-R2) ──────────────────

def test_deadline_expires_during_embedding_no_state_written():
    """
    Verify that when a real Pipeline.process_document() deadline expires during
    the embedding stage, it aborts cleanly with ProcessingTimeoutError and leaves
    zero vector files, zero registry entries, and zero SQLite records.
    """
    import fitz
    import numpy as np

    tmp_dir = tempfile.mkdtemp(prefix="hamigenz_embed_deadline_")
    try:
        vectors_dir = os.path.join(tmp_dir, "vectors")
        db_path = os.path.join(tmp_dir, "test.db")
        upload_path = os.path.join(tmp_dir, "test.pdf")

        # Create valid PDF with text
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 72), "Line for embedding timeout verification.\n" * 5)
        doc.save(upload_path)
        doc.close()

        doc_id = "doc_embed_timeout"
        # Set generous deadline for extraction and chunking, then cross it explicitly during embedding
        deadline = time.monotonic() + 1.0

        def slow_embed_texts(texts):
            rem = deadline - time.monotonic()
            if rem > 0:
                time.sleep(rem + 0.05)
            return np.zeros((len(texts), 384), dtype=np.float32)

        embedder = MagicMock()
        embedder.dimension = 384
        embedder.embed_texts.side_effect = slow_embed_texts

        vstore = VectorStore(vectors_dir=vectors_dir, dimension=384)
        chunker = Chunker(chunk_size=500, overlap=10)
        metadata = MetadataStore(db_path=db_path)

        pipeline = Pipeline(
            embedding_service=embedder,
            vector_store=vstore,
            chunker=chunker,
            metadata_store=metadata,
        )

        with pytest.raises(ProcessingTimeoutError) as exc_info:
            pipeline.process_document(
                filepath=upload_path,
                doc_id=doc_id,
                filename="test.pdf",
                session_id="session_embed_test",
                deadline=deadline,
            )

        assert "embedding" in str(exc_info.value).lower()

        # Invariant: No vector artifacts on disk
        faiss_file = os.path.join(vectors_dir, f"{doc_id}.faiss")
        meta_file = os.path.join(vectors_dir, f"{doc_id}_meta.json")
        assert not os.path.exists(faiss_file), "Ghost FAISS index was created on disk!"
        assert not os.path.exists(meta_file), "Ghost vector metadata was created on disk!"

        # Invariant: Doc id not in vector store registry
        assert doc_id not in vstore._doc_indices

        # Invariant: No SQLite records
        assert metadata.get_document(doc_id, session_id="session_embed_test") is None
        conn = metadata._get_connection()
        chunk_count = conn.execute("SELECT count(*) FROM chunks WHERE doc_id=?", (doc_id,)).fetchone()[0]
        conn.close()
        assert chunk_count == 0, "Ghost chunks were committed to SQLite!"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─── 11. Persistence Failure Triggers Atomic Rollback (Task 2.1.1-R2) ──────

def test_persistence_failure_triggers_atomic_rollback():
    """
    Inject a failure during the persistence stage and verify that the atomic
    rollback leaves no document or chunk records in SQLite and no vector artifacts
    on disk or in memory.
    """
    import fitz
    import numpy as np

    tmp_dir = tempfile.mkdtemp(prefix="hamigenz_rollback_test_")
    try:
        vectors_dir = os.path.join(tmp_dir, "vectors")
        db_path = os.path.join(tmp_dir, "test.db")
        upload_path = os.path.join(tmp_dir, "test.pdf")

        # Create valid PDF with text
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 72), "Text for rollback verification.\n" * 5)
        doc.save(upload_path)
        doc.close()

        embedder = MagicMock()
        embedder.dimension = 384
        embedder.embed_texts.return_value = np.zeros((1, 384), dtype=np.float32)

        vstore = VectorStore(vectors_dir=vectors_dir, dimension=384)
        chunker = Chunker(chunk_size=500, overlap=10)
        metadata = MetadataStore(db_path=db_path)

        # Inject error into metadata.add_chunks (after vector store has written)
        def failing_add_chunks(chunks):
            raise RuntimeError("Injected disk failure during chunk metadata write")
        metadata.add_chunks = failing_add_chunks

        pipeline = Pipeline(
            embedding_service=embedder,
            vector_store=vstore,
            chunker=chunker,
            metadata_store=metadata,
        )

        doc_id = "doc_rollback_01"
        generous_deadline = time.monotonic() + 10.0

        with pytest.raises(RuntimeError) as exc_info:
            pipeline.process_document(
                filepath=upload_path,
                doc_id=doc_id,
                filename="test.pdf",
                session_id="session_rollback",
                deadline=generous_deadline,
            )

        assert "Injected disk failure" in str(exc_info.value)

        # Verify atomic rollback cleaned up vector artifacts
        faiss_file = os.path.join(vectors_dir, f"{doc_id}.faiss")
        meta_file = os.path.join(vectors_dir, f"{doc_id}_meta.json")
        assert not os.path.exists(faiss_file), "FAISS index was not rolled back!"
        assert not os.path.exists(meta_file), "Vector meta file was not rolled back!"
        assert doc_id not in vstore._doc_indices, "Doc ID remained in vector store index!"

        # Verify atomic rollback cleaned up database records
        assert metadata.get_document(doc_id, session_id="session_rollback") is None
        conn = metadata._get_connection()
        chunk_count = conn.execute("SELECT count(*) FROM chunks WHERE doc_id=?", (doc_id,)).fetchone()[0]
        conn.close()
        assert chunk_count == 0, "Partial chunks were left in database!"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─── 12. Deadline Crossing During Persistence (Task 2.1.1-R2) ─────────────

def test_deadline_crossing_during_persistence_never_returns_503(mock_pipeline):
    """
    Verify that when the deadline is crossed while persistence is executing:
    1. The route does NOT return HTTP 503.
    2. The route waits for the persistence stage to finish.
    3. The request completes with HTTP 200 and matches the committed state.
    """
    async def _run():
        test_sem = asyncio.Semaphore(1)
        persistence_entered = threading.Event()

        def slow_persistence_worker(filepath, doc_id, filename, session_id=None, deadline=None):
            persistence_entered.set()
            # Simulate crossing deadline during persistence
            time.sleep(0.08)
            # Persistence completes successfully
            return {
                "status": "success",
                "doc_id": doc_id,
                "filename": filename,
                "pages": 1,
                "chunks": 1,
                "language_hint": "english",
            }

        mock_pipeline.process_document.side_effect = slow_persistence_worker
        valid_pdf_bytes = b"%PDF-1.4\n" + b"0" * 200

        with patch.object(main, "get_processing_semaphore", return_value=test_sem):
            with patch.dict(os.environ, {"HAMIGENZ_PROCESSING_TIMEOUT_SECONDS": "0.04"}):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                    resp = await client.post(
                        "/upload",
                        files={"file": ("test.pdf", valid_pdf_bytes, "application/pdf")},
                    )

                    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
                    assert resp.json()["doc_id"] is not None
                    assert resp.json()["pages"] == 1
                    assert not test_sem.locked()
                    assert test_sem._value == 1

    asyncio.run(_run())


# ─── 13. Cancellation Racing With Failed Worker Cleanup (Task 2.1.1-R3) ────

def test_cancellation_racing_with_timeout_cleans_up_upload(mock_pipeline):
    """
    Verify that if a worker encounters ProcessingTimeoutError and the HTTP
    request is cancelled concurrently (or right as it completes), the supervisor
    reliably cleans up the upload file, releases the permit, and deregisters itself.
    """
    async def _run():
        test_sem = asyncio.Semaphore(1)
        worker_started = threading.Event()
        allow_worker_fail = threading.Event()
        saved_filepath = None

        def timing_out_worker(filepath, *args, **kwargs):
            nonlocal saved_filepath
            saved_filepath = filepath
            worker_started.set()
            allow_worker_fail.wait(timeout=5.0)
            raise ProcessingTimeoutError("Processing deadline exceeded in worker")

        mock_pipeline.process_document.side_effect = timing_out_worker
        valid_pdf_bytes = b"%PDF-1.4\n" + b"0" * 200

        with patch.object(main, "get_processing_semaphore", return_value=test_sem):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                req_task = asyncio.create_task(
                    client.post("/upload", files={"file": ("timeout_race.pdf", valid_pdf_bytes, "application/pdf")})
                )

                for _ in range(200):
                    if worker_started.is_set():
                        break
                    await asyncio.sleep(0.01)
                assert worker_started.is_set(), "Worker did not start in time"
                assert saved_filepath is not None
                assert os.path.exists(saved_filepath)

                # Cancel the HTTP request coroutine
                req_task.cancel()
                try:
                    await req_task
                except (asyncio.CancelledError, httpx.RequestError):
                    pass

                # Allow the worker to complete its failure
                allow_worker_fail.set()

                # Wait for any active supervisor tasks to finish terminal processing
                active = main.get_active_supervisor_tasks()
                if active:
                    await asyncio.gather(*list(active), return_exceptions=True)

                # Supervisor must have cleaned up the file and released the permit
                assert not os.path.exists(saved_filepath), "Failed upload file was not cleaned up!"
                assert not test_sem.locked()
                assert test_sem._value == 1
                assert len(main.get_active_supervisor_tasks()) == 0

    asyncio.run(_run())


def test_cancellation_racing_with_worker_error_cleans_up_upload(mock_pipeline):
    """
    Verify that if a worker raises an unhandled exception and the request
    is cancelled, supervisor-owned cleanup unlinks the file and releases permit.
    """
    async def _run():
        test_sem = asyncio.Semaphore(1)
        worker_started = threading.Event()
        allow_worker_fail = threading.Event()
        saved_filepath = None

        def failing_worker(filepath, *args, **kwargs):
            nonlocal saved_filepath
            saved_filepath = filepath
            worker_started.set()
            allow_worker_fail.wait(timeout=5.0)
            raise RuntimeError("Fatal worker parsing error")

        mock_pipeline.process_document.side_effect = failing_worker
        valid_pdf_bytes = b"%PDF-1.4\n" + b"0" * 200

        with patch.object(main, "get_processing_semaphore", return_value=test_sem):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                req_task = asyncio.create_task(
                    client.post("/upload", files={"file": ("error_race.pdf", valid_pdf_bytes, "application/pdf")})
                )

                for _ in range(200):
                    if worker_started.is_set():
                        break
                    await asyncio.sleep(0.01)
                assert worker_started.is_set(), "Worker did not start in time"
                assert saved_filepath is not None
                assert os.path.exists(saved_filepath)

                # Cancel the request coroutine
                req_task.cancel()
                try:
                    await req_task
                except (asyncio.CancelledError, httpx.RequestError):
                    pass

                allow_worker_fail.set()

                active = main.get_active_supervisor_tasks()
                if active:
                    await asyncio.gather(*list(active), return_exceptions=True)

                assert not os.path.exists(saved_filepath), "Corrupted upload file was not cleaned up!"
                assert not test_sem.locked()
                assert test_sem._value == 1
                assert len(main.get_active_supervisor_tasks()) == 0

    asyncio.run(_run())


def test_cancellation_with_exceeded_page_limit_cleans_up_representations(mock_pipeline):
    """
    Verify that if a worker succeeds but exceeds the page limit, and the caller
    is cancelled, supervisor-owned cleanup evicts the vector/metadata representations
    and unlinks the file.
    """
    async def _run():
        test_sem = asyncio.Semaphore(1)
        worker_started = threading.Event()
        allow_worker_finish = threading.Event()
        saved_filepath = None

        def large_doc_worker(filepath, doc_id, filename, *args, **kwargs):
            nonlocal saved_filepath
            saved_filepath = filepath
            worker_started.set()
            allow_worker_finish.wait(timeout=5.0)
            return {
                "status": "success",
                "doc_id": doc_id,
                "filename": filename,
                "pages": 250,  # Exceeds MAX_PAGES (200)
                "chunks": 250,
                "language_hint": "english",
            }

        mock_pipeline.process_document.side_effect = large_doc_worker
        valid_pdf_bytes = b"%PDF-1.4\n" + b"0" * 200

        with patch.object(main, "get_processing_semaphore", return_value=test_sem):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                req_task = asyncio.create_task(
                    client.post("/upload", files={"file": ("too_large.pdf", valid_pdf_bytes, "application/pdf")})
                )

                for _ in range(200):
                    if worker_started.is_set():
                        break
                    await asyncio.sleep(0.01)
                assert worker_started.is_set()
                assert saved_filepath is not None

                req_task.cancel()
                try:
                    await req_task
                except (asyncio.CancelledError, httpx.RequestError):
                    pass

                allow_worker_finish.set()

                active = main.get_active_supervisor_tasks()
                if active:
                    await asyncio.gather(*list(active), return_exceptions=True)

                # Supervisor must have cleaned up the file, vector store, and metadata
                assert not os.path.exists(saved_filepath), "Oversized upload file was not unlinked!"
                app.state.vector_store.remove_document.assert_called()
                app.state.metadata.delete_document.assert_called()
                assert not test_sem.locked()
                assert test_sem._value == 1

    asyncio.run(_run())


def test_cancellation_with_valid_document_preserves_committed_state(mock_pipeline):
    """
    Verify that if a worker completes successfully with a valid document within limits,
    cancelling the HTTP request does NOT delete the committed document data or file.
    """
    async def _run():
        test_sem = asyncio.Semaphore(1)
        worker_started = threading.Event()
        allow_worker_finish = threading.Event()
        saved_filepath = None

        def valid_worker(filepath, doc_id, filename, *args, **kwargs):
            nonlocal saved_filepath
            saved_filepath = filepath
            worker_started.set()
            allow_worker_finish.wait(timeout=5.0)
            return {
                "status": "success",
                "doc_id": doc_id,
                "filename": filename,
                "pages": 2,
                "chunks": 4,
                "language_hint": "english",
            }

        mock_pipeline.process_document.side_effect = valid_worker
        valid_pdf_bytes = b"%PDF-1.4\n" + b"0" * 200

        with patch.object(main, "get_processing_semaphore", return_value=test_sem):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                req_task = asyncio.create_task(
                    client.post("/upload", files={"file": ("valid_cancelled.pdf", valid_pdf_bytes, "application/pdf")})
                )

                for _ in range(200):
                    if worker_started.is_set():
                        break
                    await asyncio.sleep(0.01)
                assert worker_started.is_set()
                assert saved_filepath is not None

                # Client cancels/disconnects while worker is finishing
                req_task.cancel()
                try:
                    await req_task
                except (asyncio.CancelledError, httpx.RequestError):
                    pass

                allow_worker_finish.set()

                active = main.get_active_supervisor_tasks()
                if active:
                    await asyncio.gather(*list(active), return_exceptions=True)

                # Valid committed file and representations must remain intact!
                assert os.path.exists(saved_filepath), "Valid committed upload file was accidentally deleted!"
                # Permit must be released
                assert not test_sem.locked()
                assert test_sem._value == 1
                assert len(main.get_active_supervisor_tasks()) == 0

                # Clean up the file created for this test
                try:
                    os.unlink(saved_filepath)
                except OSError:
                    pass

    asyncio.run(_run())
