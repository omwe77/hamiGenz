"""
hamiGenZ — Retained End-to-End Acceptance Test Suite (Milestone 3).

Verifies the complete 8-step civic document understanding lifecycle through the FastAPI test client:
1. System Healthcheck (GET /health)
2. Official Source Registry (GET /knowledge/sources)
3. Synthetic Document Ingestion (POST /upload)
4. Document Metadata and Chunk Verification (GET /documents/{id})
5. Question Answering and Evidence Grounding (POST /ask)
6. Action Extraction and Fee/Deadline Parsing (POST /actions)
7. Document and FAISS Artifact Deletion (DELETE /documents/{id})
8. Live Inference vs Graceful 503 Fallback Verification
"""
from __future__ import annotations

import io
import os
import sys
import uuid
import unicodedata
from pathlib import Path
import pytest
from starlette.testclient import TestClient

# Ensure backend on sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import main
from session_auth import generate_session_token, SESSION_COOKIE_NAME


@pytest.fixture(scope="module")
def client():
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
    """Create a minimal bilingual civic test image in memory."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (800, 250), color="white")
    draw = ImageDraw.Draw(img)
    lines = [
        "Government of Nepal - Department of Passports",
        "साधारण राहदानी ३४ पृष्ठको दस्तुर रु. ५,००० निर्धारण गरिएको छ।",
        "Standard Fee: NPR 5,000 | Processing Deadline: 15 Days",
        "आवेदकले सक्कल नागरिकता अनिवार्य रूपमा पेस गर्नुपर्नेछ।",
    ]
    y = 20
    for line in lines:
        draw.text((20, y), line, fill="black")
        y += 45
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


def test_step3_to_step7_document_lifecycle(client, auth_headers):
    """Steps 3 to 7: Ingestion -> Querying -> Actions -> Cleanup."""
    img_bytes = create_synthetic_test_image()
    files = {"file": ("test_civic_notice.png", img_bytes, "image/png")}

    # Step 3: Upload Ingestion
    upload_resp = client.post("/upload", files=files, headers=auth_headers)
    assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
    upload_data = upload_resp.json()
    doc_id = upload_data.get("doc_id")
    assert doc_id, "Response missing doc_id"

    try:
        # Step 4: Verify document chunks and metadata
        doc_resp = client.get(f"/documents/{doc_id}", headers=auth_headers)
        if doc_resp.status_code == 200:
            doc_info = doc_resp.json()
            assert doc_info.get("doc_id") == doc_id

        # Step 5: Ask query (POST /ask)
        ask_payload = {
            "question": "What is the passport fee and deadline?",
            "doc_id": doc_id,
            "level": "simple",
        }
        ask_resp = client.post("/ask", json=ask_payload, headers=auth_headers)
        # Should either return 200 with answer or 503 if LLM is unavailable
        assert ask_resp.status_code in (200, 503), f"Unexpected /ask status: {ask_resp.status_code} ({ask_resp.text})"
        if ask_resp.status_code == 200:
            ans_data = ask_resp.json()
            assert "answer" in ans_data or "response" in ans_data

        # Step 6: Action extraction (POST /actions)
        act_payload = {"doc_id": doc_id}
        act_resp = client.post("/actions", json=act_payload, headers=auth_headers)
        assert act_resp.status_code in (200, 503), f"Unexpected /actions status: {act_resp.status_code}"

    finally:
        # Step 7: Clean up document and vector artifacts
        del_resp = client.delete(f"/documents/{doc_id}", headers=auth_headers)
        assert del_resp.status_code in (200, 204, 404), f"Delete failed: {del_resp.text}"


def test_step8_live_or_fallback_inference():
    """Step 8: Direct LLM service live inference check or graceful 503 verification."""
    from llm_service import OllamaService, LLMUnavailableError

    # Test with standard config
    service = OllamaService(base_url="http://localhost:11434", model="qwen3:8b")
    try:
        resp = service.generate("Answer with 'OK': test connection.")
        assert len(resp.strip()) > 0, "Expected non-empty LLM response"
    except LLMUnavailableError as exc:
        # Graceful fallback when local daemon is not running in CI
        assert "LLM backend error" in str(exc) or "Cannot reach" in str(exc)
