"""
hamiGenZ — Retained End-to-End Acceptance Test Suite (Milestone 3 Hardening).

Verifies the complete 8-step civic document understanding lifecycle through the FastAPI test client:
1. System Healthcheck (GET /health)
2. Official Source Registry (GET /knowledge/sources)
3. Synthetic Document Ingestion (POST /upload)
4. Document Metadata and Chunk Verification (GET /documents/{id}/viewer & GET /documents)
5. Question Answering and Evidence Grounding (POST /ask - Deterministic Mocked Verification)
6. Action Extraction and Fee/Deadline Parsing (POST /actions)
7. Cross-Session Isolation & Document Deletion (DELETE /documents/{id} & Disk Cleanup Verification)
8. Graceful Offline 503 Handling vs Opt-In Live Inference (HAMIGENZ_LIVE_LLM_TESTS=1)
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path
import pytest
from starlette.testclient import TestClient

# Ensure backend on sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import main
from main import UPLOAD_DIR, VECTORS_DIR
from session_auth import generate_session_token, SESSION_COOKIE_NAME
from llm_service import LLMUnavailableError, OllamaService
from tests.evaluation.generate_ocr_corpus import get_font


@pytest.fixture
def client():
    # Function-scoped so conftest.py's autouse mock_offline_embeddings patches
    # main.EmbeddingService before TestClient triggers FastAPI lifespan startup.
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def auth_headers():
    token = generate_session_token()
    return {
        "Cookie": f"{SESSION_COOKIE_NAME}={token}",
        "X-Session-Token": token,
    }


def create_synthetic_test_image() -> bytes:
    """Create a minimal bilingual civic test image in memory using a verified font."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (900, 300), color="white")
    draw = ImageDraw.Draw(img)
    font = get_font(size=24)
    lines = [
        "Government of Nepal - Department of Passports",
        "साधारण राहदानी ३४ पृष्ठको दस्तुर रु. ५,००० निर्धारण गरिएको छ।",
        "Standard Fee: NPR 5,000 | Processing Deadline: 15 Days",
        "आवेदकले सक्कल नागरिकता अनिवार्य रूपमा पेस गर्नुपर्नेछ।",
    ]
    y = 25
    for line in lines:
        draw.text((25, y), line, fill=(15, 23, 42), font=font)
        y += 55
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_step1_health_check(client):
    """Step 1: Verify health endpoint."""
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    data = resp.json()
    assert data.get("status") in ("ok", "healthy")


def test_step2_official_sources(client):
    """Step 2: Verify official government source registry."""
    resp = client.get("/knowledge/sources")
    assert resp.status_code == 200
    data = resp.json()
    sources = data.get("sources", [])
    assert len(sources) >= 5, f"Expected at least 5 curated sources, got {len(sources)}"
    urls = [s.get("url", "") for s in sources]
    assert any(".gov.np" in u for u in urls), "Expected .gov.np portals in official source registry"


def test_step3_to_step7_document_lifecycle(client, auth_headers, monkeypatch):
    """
    Steps 3 to 7: Deterministic End-to-End Document Lifecycle.
    Covers upload ingestion, viewer metadata, cross-session isolation,
    grounded Q&A with citations, action extraction schema validation,
    and rigorous disk cleanup verification.

    Cleanup (Step 7) runs in `finally` unconditionally from before upload,
    so a mid-test assertion failure cannot leave orphaned files or vector
    indexes. `doc_id` is initialised to `None` before the try block; the
    finally guard skips cleanup only when upload never issued a usable doc_id.
    If the test body already failed, cleanup errors are recorded without
    hiding the original test failure.
    """
    img_bytes = create_synthetic_test_image()
    files = {"file": ("test_civic_notice.png", img_bytes, "image/png")}

    # Initialise before try so finally can always reference doc_id.
    doc_id: str | None = None
    filepath: str | None = None

    try:
        # Step 3: Upload Ingestion — inside try so cleanup always runs.
        upload_resp = client.post("/upload", files=files, headers=auth_headers)
        assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
        upload_data = upload_resp.json()
        doc_id = upload_data.get("doc_id")
        assert doc_id, "Response missing doc_id"

        # Capture physical paths immediately so finally can verify removal even if
        # later assertions abort early.
        uploaded_files = list(UPLOAD_DIR.glob(f"*{doc_id}*"))
        filepath = str(uploaded_files[0]) if uploaded_files else None

        assert upload_data.get("filename") == "test_civic_notice.png"
        assert upload_data.get("chunks", 0) > 0, "Expected at least 1 chunk created"
        assert len(uploaded_files) >= 1, f"Uploaded file matching *{doc_id}* not found in {UPLOAD_DIR}"
        assert len(list(VECTORS_DIR.glob(f"{doc_id}*"))) >= 1, "Expected FAISS vector artifacts on disk"

        # Step 4: Verify document metadata & viewer extraction
        viewer_resp = client.get(f"/documents/{doc_id}/viewer", headers=auth_headers)
        assert viewer_resp.status_code == 200, (
            f"Viewer failed ({viewer_resp.status_code}): {viewer_resp.text}"
        )
        viewer_data = viewer_resp.json()
        assert viewer_data.get("doc_id") == doc_id
        assert viewer_data.get("filename") == "test_civic_notice.png"
        assert len(viewer_data.get("pages", [])) > 0, "Expected at least 1 page in viewer data"
        assert len(viewer_data["pages"][0].get("text", "").strip()) > 0, "Extracted text is empty"

        # Verify listing in /documents
        list_resp = client.get("/documents", headers=auth_headers)
        assert list_resp.status_code == 200
        user_docs = list_resp.json()
        assert any(d.get("doc_id") == doc_id for d in user_docs), "Document not listed in /documents"

        # Cross-Session Isolation Verification:
        # Another session must NOT be able to view, query, or delete this document
        token_b = generate_session_token()
        auth_b = {
            "Cookie": f"{SESSION_COOKIE_NAME}={token_b}",
            "X-Session-Token": token_b,
        }
        b_viewer_resp = client.get(f"/documents/{doc_id}/viewer", headers=auth_b)
        assert b_viewer_resp.status_code == 404, "Session B must not access Session A's document viewer"

        b_ask_resp = client.post("/ask", json={"question": "fee?", "doc_id": doc_id}, headers=auth_b)
        assert b_ask_resp.status_code == 404, "Session B must not query Session A's document"

        b_del_resp = client.delete(f"/documents/{doc_id}", headers=auth_b)
        assert b_del_resp.status_code == 404, "Session B must not delete Session A's document"

        # Step 5: Deterministic Question Answering (POST /ask)
        # Mock primary LLM + independent evaluator to verify deterministic pipeline,
        # citation grounding, and verification layer without self-evaluation.
        deterministic_answer = (
            "According to the document (Page 1), the standard passport fee is NPR 5,000 for 34 pages."
        )
        monkeypatch.setattr(main.app.state.llm, "generate", lambda prompt: deterministic_answer)

        class _MockIndependentEvaluator:
            def generate_structured(self, prompt: str) -> dict:
                return {
                    "overall_confidence": "HIGH",
                    "claims": [
                        {
                            "claim": "The standard passport fee is NPR 5,000 for 34 pages.",
                            "classification": "SUPPORTED",
                            "evidence": "Document text states Standard Fee: NPR 5,000.",
                            "page_refs": [1],
                        }
                    ],
                    "missing_evidence": [],
                    "warning": "",
                }

        monkeypatch.setattr(main.app.state.validator, "llm", _MockIndependentEvaluator())
        monkeypatch.setattr(main.app.state.verification, "_is_independent", True)

        ask_payload = {
            "question": "What is the passport fee?",
            "doc_id": doc_id,
            "level": "simple",
        }
        ask_resp = client.post("/ask", json=ask_payload, headers=auth_headers)
        assert ask_resp.status_code == 200, f"/ask failed: {ask_resp.status_code} ({ask_resp.text})"
        ans_data = ask_resp.json()
        assert "5,000" in ans_data.get("answer", "") or "5000" in ans_data.get("answer", "")
        assert 1 in ans_data.get("evidence_pages", []), f"Expected page 1 in evidence_pages: {ans_data.get('evidence_pages')}"
        # Citations must be present and linked to the document
        citations = ans_data.get("citations", [])
        assert len(citations) > 0, "Expected at least one grounded citation linked to document"
        assert any(
            c.get("page") == 1 and (
                "5,000" in c.get("excerpt", "")
                or "राहदानी" in c.get("excerpt", "")
                or "Passports" in c.get("excerpt", "")
                or "Fee" in c.get("excerpt", "")
            )
            for c in citations
        ), f"Citation did not contain document evidence: {citations}"
        assert ans_data.get("grounding", {}).get("confidence_score") is not None

        # Step 6: Action extraction (POST /actions)
        # Force hints_only fallback: LLMUnavailableError must yield meta.status == "hints_only"
        def _raise_unavailable(*args, **kwargs):
            raise LLMUnavailableError("Simulated offline for action hint extraction")

        monkeypatch.setattr(main.app.state.llm, "generate_structured", _raise_unavailable)
        act_payload = {"doc_id": doc_id}
        act_resp = client.post("/actions", json=act_payload, headers=auth_headers)
        assert act_resp.status_code == 200, f"/actions failed: {act_resp.status_code} ({act_resp.text})"
        act_data = act_resp.json()
        for field in ("requirements", "deadlines", "fees", "eligibility", "next_steps", "official_links", "meta"):
            assert field in act_data, f"Action extraction response missing field '{field}'"
        assert isinstance(act_data["requirements"], list)
        assert isinstance(act_data["fees"], list)
        assert isinstance(act_data["deadlines"], list)
        # LLMUnavailableError must yield "hints_only", not generic "error".
        assert act_data["meta"].get("status") == "hints_only", (
            f"Expected hints_only status when LLM unavailable, got: {act_data['meta'].get('status')!r}"
        )

    finally:
        # Step 7: Document and FAISS Artifact Deletion — always runs when doc_id was obtained.
        # Guard on doc_id so a failed upload (no id issued) doesn't attempt a None-keyed delete.
        # If the try block already raised, do not let a cleanup error mask the original failure.
        has_primary_failure = sys.exc_info()[0] is not None
        if doc_id is not None:
            try:
                del_resp = client.delete(f"/documents/{doc_id}", headers=auth_headers)
                # Accept 200 (successful delete) or 404 (never persisted due to early failure).
                assert del_resp.status_code in (200, 404), (
                    f"Delete returned unexpected status: {del_resp.status_code} ({del_resp.text})"
                )
                if del_resp.status_code == 200:
                    del_data = del_resp.json()
                    assert del_data.get("status") == "deleted"
                    assert del_data.get("doc_id") == doc_id

                # Verify physical file removal (file may not exist if upload failed)
                if filepath and Path(filepath).exists():
                    raise AssertionError(f"Uploaded file was not unlinked from disk: {filepath}")

                # Verify vector index artifacts removal
                vector_artifacts = list(VECTORS_DIR.glob(f"{doc_id}*"))
                assert len(vector_artifacts) == 0, f"Vector artifacts still present after deletion: {vector_artifacts}"

                # Verify metadata removal from API
                after_viewer_resp = client.get(f"/documents/{doc_id}/viewer", headers=auth_headers)
                assert after_viewer_resp.status_code == 404, "Document viewer should return 404 after deletion"

                after_list_resp = client.get("/documents", headers=auth_headers)
                assert not any(d.get("doc_id") == doc_id for d in after_list_resp.json()), (
                    "Document still listed in /documents after deletion"
                )

                # Idempotent/duplicate deletion should return 404
                second_del_resp = client.delete(f"/documents/{doc_id}", headers=auth_headers)
                assert second_del_resp.status_code == 404, "Subsequent deletion should return 404"
            except Exception as cleanup_exc:
                if not has_primary_failure:
                    raise
                print(f"\n[E2E CLEANUP WARNING] Cleanup failed after primary test error: {cleanup_exc}")


def test_offline_graceful_503_when_llm_unavailable(client, auth_headers, monkeypatch):
    """Verify that when Ollama/LLM backend is unavailable, /ask cleanly returns 503 without leaking stack trace."""
    img_bytes = create_synthetic_test_image()
    upload_resp = client.post(
        "/upload",
        files={"file": ("test_503_notice.png", img_bytes, "image/png")},
        headers=auth_headers,
    )
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["doc_id"]

    try:
        def mock_llm_unavailable(*args, **kwargs):
            raise LLMUnavailableError("Ollama daemon is offline on 127.0.0.1:11434")

        monkeypatch.setattr(main.app.state.llm, "generate", mock_llm_unavailable)

        ask_resp = client.post(
            "/ask",
            json={"question": "What is the fee?", "doc_id": doc_id},
            headers=auth_headers,
        )
        assert ask_resp.status_code == 503, f"Expected 503 when LLM unavailable, got {ask_resp.status_code}"
        data = ask_resp.json()
        assert "detail" in data
        assert "temporarily unavailable" in data["detail"].lower() or "ai backend" in data["detail"].lower()
    finally:
        client.delete(f"/documents/{doc_id}", headers=auth_headers)


@pytest.mark.skipif(
    os.getenv("HAMIGENZ_LIVE_LLM_TESTS") != "1",
    reason="Live LLM tests are opt-in (set HAMIGENZ_LIVE_LLM_TESTS=1). Skipped in normal CI.",
)
def test_live_ollama_qwen_inference():
    """
    Opt-in live inference test against local Ollama Qwen3:8b model.
    Runs only when HAMIGENZ_LIVE_LLM_TESTS=1. Never silently reported as pass if skipped.
    """
    service = OllamaService(base_url="http://localhost:11434", model="qwen3:8b")
    start = time.time()
    # Test generation in Nepali
    prompt = "नेपालको राजधानी शहर कुन हो? एक शब्दमा उत्तर दिनुहोस्।"
    resp = service.generate(prompt).strip()
    elapsed = time.time() - start

    assert len(resp) > 0, "Live LLM returned empty response"
    # Qwen3:8b should identify Kathmandu in Nepali or English
    assert any(token in resp for token in ("काठमाडौँ", "काठमाडौं", "Kathmandu")), (
        f"Unexpected capital city response: {resp}"
    )

    # Preserve sanitized execution evidence.
    # Only write if the file does not already exist so a tracked baseline result
    # (e.g. committed to docs/evidence/) is not silently replaced on every run.
    evidence_dir = Path(__file__).resolve().parent.parent / "docs" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "live_llm_execution.json"
    if not evidence_file.exists():
        evidence_data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model": "qwen3:8b",
            "provider": "ollama",
            "prompt": prompt,
            "response": resp,
            "elapsed_seconds": round(elapsed, 2),
            "status": "PASS",
        }
        evidence_file.write_text(json.dumps(evidence_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n[LIVE LLM] qwen3:8b response in {elapsed:.2f}s: '{resp}' (evidence saved to {evidence_file})")
    else:
        print(f"\n[LIVE LLM] qwen3:8b response in {elapsed:.2f}s: '{resp}' (evidence already tracked at {evidence_file}, not overwritten)")
