"""
Focused tests for the staged zero-cost AI architecture:
- Feature flags, ZDR pre-flight gate, and Gemini synthetic-only restriction
- Groq GPT-OSS 120B & Cloudflare Qwen3.8-27B token budgets, HTTP 429, and QuotaTracker
- Server-side evaluator JSON schema validation (never failing open)
- Explicit verification_status states
- Safe SQLite answer caching and actual document-retention cleanup
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from document_processor import MetadataStore
from llm_service import (
    CloudflareWorkersAIService,
    GroqService,
    GroundingValidator,
    LLMRateLimitError,
    LLMUnavailableError,
    QuotaTracker,
    VerificationLayer,
    validate_evaluator_payload,
)
import main as backend_main


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict, headers: dict | None = None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class TestFeatureFlagsAndGates:
    def test_gemini_blocked_without_synthetic_flag(self):
        with pytest.raises(ValueError, match="synthetic-data testing"):
            backend_main.build_llm_and_evaluator(
                llm_provider="gemini",
                gemini_api_key="test-key",
                gemini_synthetic_testing_only=False,
                public_production_mode=False,
            )

    def test_gemini_blocked_in_public_production_mode(self):
        with pytest.raises(ValueError, match="synthetic-data testing"):
            backend_main.build_llm_and_evaluator(
                llm_provider="gemini",
                gemini_api_key="test-key",
                gemini_synthetic_testing_only=True,
                public_production_mode=True,
            )

    def test_groq_blocked_without_zdr_verified(self):
        with pytest.raises(ValueError, match="ZDR_VERIFIED=true"):
            backend_main.build_llm_and_evaluator(
                llm_provider="groq",
                groq_api_key="gsk_test",
                zdr_verified=False,
            )

    def test_groq_and_cloudflare_evaluator_enabled_with_zdr(self):
        primary, evaluator = backend_main.build_llm_and_evaluator(
            llm_provider="groq",
            groq_api_key="gsk_test",
            enable_independent_evaluator=True,
            evaluator_provider="cloudflare",
            cf_account_id="acct-123",
            cf_api_token="cf-tok-456",
            zdr_verified=True,
        )
        assert isinstance(primary, GroqService)
        assert primary.model == "openai/gpt-oss-120b"
        assert isinstance(evaluator, CloudflareWorkersAIService)
        assert evaluator.model == "@cf/qwen/qwen3.8-27b"


class TestProvidersQuotaAnd429:
    def test_groq_enforces_token_budget_and_handles_429(self):
        session = MagicMock()
        session.post.return_value = _FakeResponse(
            429, {"error": {"message": "rate limit"}}, headers={"Retry-After": "42"}
        )
        svc = GroqService(
            api_key="gsk_secret_123",
            max_input_tokens=10,
            max_output_tokens=50,
            session=session,
        )
        with pytest.raises(LLMRateLimitError) as exc_info:
            svc.generate("A" * 500, options={"max_tokens": 9999})
        assert exc_info.value.retry_after == 42
        sent_payload = session.post.call_args.kwargs["json"]
        assert sent_payload["max_tokens"] == 50
        assert "[truncated to token budget]" in sent_payload["messages"][0]["content"]

    def test_cloudflare_qwen_extracts_response_and_handles_429(self):
        session = MagicMock()
        session.post.side_effect = [
            _FakeResponse(200, {"success": True, "result": {"response": '{"claims": []}'}}),
            _FakeResponse(429, {"success": False}, headers={"Retry-After": "15"}),
        ]
        svc = CloudflareWorkersAIService(
            account_id="acct",
            api_token="tok",
            session=session,
        )
        out = svc.generate("Evaluate this")
        assert out == '{"claims": []}'
        with pytest.raises(LLMRateLimitError) as exc_info:
            svc.generate("Second call")
        assert exc_info.value.retry_after == 15

    def test_quota_tracker_blocks_when_tpm_or_rpd_exhausted(self):
        qt = QuotaTracker("test", rpm=2, rpd=5, tpm=100, tpd=500)
        qt.check_and_reserve(60)
        with pytest.raises(LLMRateLimitError, match="TPM"):
            qt.check_and_reserve(50)


class TestSchemaValidationAndVerificationStates:
    def test_server_side_schema_rejects_malformed_qwen_output(self):
        bad_outputs = [
            {"error": "Could not parse JSON response"},
            {"claims": "not-a-list", "overall_confidence": "HIGH"},
            {"claims": [{"claim": "Fee is 500", "classification": "MAYBE"}], "overall_confidence": "HIGH"},
            {"claims": [], "overall_confidence": "SUPER_HIGH"},
        ]
        for payload in bad_outputs:
            ok, normalized, _ = validate_evaluator_payload(payload)
            assert not ok
            assert normalized is None

    def test_verification_layer_never_fails_open_on_bad_json_or_429(self):
        bad_llm = MagicMock()
        bad_llm.generate_structured.return_value = {"claims": [{"claim": "", "classification": "BAD"}], "overall_confidence": "HIGH"}
        layer = VerificationLayer(bad_llm, GroundingValidator(bad_llm))
        res = layer.verify("Q?", "A.", [{"page_num": 1, "text": "Evidence"}])
        assert res["verification_status"] == "unverified_evaluator_unavailable"
        assert res["schema_valid"] is False

        rate_llm = MagicMock()
        rate_llm.generate_structured.side_effect = LLMRateLimitError("429", retry_after=30)
        layer2 = VerificationLayer(rate_llm, GroundingValidator(rate_llm))
        res2 = layer2.verify("Q?", "A.", [{"page_num": 1, "text": "Evidence"}])
        assert res2["verification_status"] == "unverified_evaluator_unavailable"
        assert res2["schema_valid"] is False

    def test_verification_layer_distinguishes_verified_and_flagged(self):
        good_llm = MagicMock()
        good_llm.generate_structured.return_value = {
            "claims": [{"claim": "Fee is NPR 500", "classification": "SUPPORTED", "evidence": "Page 1", "page_refs": [1]}],
            "overall_confidence": "HIGH",
            "missing_evidence": [],
            "warning": "",
        }
        layer = VerificationLayer(good_llm, GroundingValidator(good_llm))
        res = layer.verify("Fee?", "NPR 500", [{"page_num": 1, "text": "Fee NPR 500"}])
        assert res["verification_status"] == "verified"
        assert res["schema_valid"] is True

        flagged_llm = MagicMock()
        flagged_llm.generate_structured.return_value = {
            "claims": [{"claim": "Fee is NPR 9999", "classification": "CONTRADICTED", "evidence": "Page 1 says 500", "page_refs": [1]}],
            "overall_confidence": "LOW",
            "missing_evidence": [],
            "warning": "Conflict",
        }
        layer_f = VerificationLayer(flagged_llm, GroundingValidator(flagged_llm))
        res_f = layer_f.verify("Fee?", "NPR 9999", [{"page_num": 1, "text": "Fee NPR 500"}])
        assert res_f["verification_status"] == "unverified_flagged"
        assert res_f["schema_valid"] is True


class TestSafeCachingAndDocumentRetention:
    def test_cache_isolated_and_purged_on_document_delete(self, tmp_path):
        db = MetadataStore(str(tmp_path / "test.db"))
        db.add_document("doc1", "sample.pdf", str(tmp_path / "sample.pdf"), 1, "nepali", session_id="sess-a")
        db.set_cached_answer("k1", "doc1", "sess-a", "GroqService", "openai/gpt-oss-120b", {"answer": "ok"}, ttl_seconds=3600)
        assert db.get_cached_answer("k1") == {"answer": "ok"}

        db.delete_document("doc1", session_id="sess-a")
        assert db.get_cached_answer("k1") is None

    def test_cleanup_expired_documents_removes_files_vectors_and_rows(self, tmp_path):
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        expired_file = upload_dir / "old_doc.pdf"
        fresh_file = upload_dir / "new_doc.pdf"
        expired_file.write_bytes(b"%PDF-1.4 old")
        fresh_file.write_bytes(b"%PDF-1.4 new")

        db = MetadataStore(str(tmp_path / "test.db"))
        db.add_document("old_doc", "old.pdf", str(expired_file), 1, "english", session_id="s1")
        db.add_document("new_doc", "new.pdf", str(fresh_file), 1, "nepali", session_id="s1")

        # Backdate old_doc last_accessed_at by 48h
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        conn = db._get_connection()
        conn.execute("UPDATE documents SET last_accessed_at=? WHERE doc_id=?", (old_ts, "old_doc"))
        conn.commit()
        conn.close()

        vs = MagicMock()
        removed = backend_main.cleanup_expired_documents(db, vs, upload_dir, retention_seconds=86400)
        assert removed == 1
        vs.remove_document.assert_called_once_with("old_doc")
        assert not expired_file.exists()
        assert fresh_file.exists()
        assert db.get_document("old_doc") is None
        assert db.get_document("new_doc") is not None
