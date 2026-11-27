"""
Focused tests for the staged zero-cost AI architecture QA requirements:
- Feature flags, ZDR pre-flight gate, and Gemini synthetic-only restriction
- Groq GPT-OSS 120B & Cloudflare Qwen3.8-27B token budgets, HTTP 429, Retry-After / x-ratelimit-reset-*, advisory QuotaTracker
- Server-side evaluator JSON schema validation (never failing open)
- Explicit verification_status semantics (evidence_checks_passed only when evaluator + deterministic checks pass; never guarantees correctness)
- Session-isolated SQLite caching & invalidation on deletion, generation, model, or prompt changes
- Periodic document-retention cleanup with active-upload protection
- General-question HTTP 429 never fabricating document fallback excerpts
"""
import asyncio
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
    def test_groq_enforces_token_budget_and_parses_ratelimit_reset(self):
        session = MagicMock()
        session.post.return_value = _FakeResponse(
            429,
            {"error": {"message": "rate limit"}},
            headers={"x-ratelimit-reset-requests": "1m30s", "x-ratelimit-remaining-requests": "0"},
        )
        svc = GroqService(
            api_key="gsk_secret_123",
            max_input_tokens=10,
            max_output_tokens=50,
            session=session,
        )
        with pytest.raises(LLMRateLimitError) as exc_info:
            svc.generate("A" * 500, options={"max_tokens": 9999})
        assert exc_info.value.retry_after == 90
        assert svc.quota.last_provider_headers.get("x-ratelimit-remaining-requests") == "0"
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

    def test_quota_tracker_is_advisory_by_default(self):
        qt = QuotaTracker("test", rpm=2, rpd=5, tpm=100, tpd=500)
        assert qt.check_and_reserve(60) is None
        warn = qt.check_and_reserve(50)
        assert warn is not None and "TPM" in warn


class TestSchemaValidationAndVerificationSemantics:
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

    def test_evidence_checks_passed_requires_both_evaluator_and_deterministic_checks(self):
        good_llm = MagicMock()
        good_llm.generate_structured.return_value = {
            "claims": [{"claim": "Fee is NPR 500", "classification": "SUPPORTED", "evidence": "Page 1", "page_refs": [1]}],
            "overall_confidence": "HIGH",
            "missing_evidence": [],
            "warning": "",
        }
        layer = VerificationLayer(good_llm, GroundingValidator(good_llm))
        res = layer.verify("Fee?", "Fee is NPR 500 (Page 1).", [{"page_num": 1, "text": "Fee NPR 500"}])
        assert res["verification_status"] == "evidence_checks_passed"
        assert res["deterministic_check_passed"] is True
        assert "not a guarantee" in res["recommendation"].lower()

        # Fabricated page citation fails deterministic check even if evaluator passed
        res_bad_page = layer.verify("Fee?", "Fee is NPR 500 (Page 99).", [{"page_num": 1, "text": "Fee NPR 500"}])
        assert res_bad_page["verification_status"] == "unverified_flagged"
        assert res_bad_page["deterministic_check_passed"] is False


class TestSafeCachingAndPeriodicRetention:
    def test_cache_isolated_across_sessions_and_invalidated_on_model_prompt_and_delete(self, tmp_path):
        db = MetadataStore(str(tmp_path / "test.db"))
        db.add_document("doc1", "sample.pdf", str(tmp_path / "sample.pdf"), 1, "nepali", session_id="sess-a")

        k_a = backend_main.build_ask_cache_key(
            session_id="sess-a", doc_id="doc1", doc_generation=0,
            llm_provider="GroqService", llm_model="openai/gpt-oss-120b",
            evaluator_provider="CloudflareWorkersAIService", evaluator_model="@cf/qwen/qwen3.8-27b",
            prompt_version="v2:abc", response_lang="nepali", question="What is the fee?",
        )
        k_b = backend_main.build_ask_cache_key(
            session_id="sess-b", doc_id="doc1", doc_generation=0,
            llm_provider="GroqService", llm_model="openai/gpt-oss-120b",
            evaluator_provider="CloudflareWorkersAIService", evaluator_model="@cf/qwen/qwen3.8-27b",
            prompt_version="v2:abc", response_lang="nepali", question="What is the fee?",
        )
        k_model = backend_main.build_ask_cache_key(
            session_id="sess-a", doc_id="doc1", doc_generation=0,
            llm_provider="GroqService", llm_model="openai/gpt-oss-20b",
            evaluator_provider="CloudflareWorkersAIService", evaluator_model="@cf/qwen/qwen3.8-27b",
            prompt_version="v2:abc", response_lang="nepali", question="What is the fee?",
        )
        k_prompt = backend_main.build_ask_cache_key(
            session_id="sess-a", doc_id="doc1", doc_generation=0,
            llm_provider="GroqService", llm_model="openai/gpt-oss-120b",
            evaluator_provider="CloudflareWorkersAIService", evaluator_model="@cf/qwen/qwen3.8-27b",
            prompt_version="v3:xyz", response_lang="nepali", question="What is the fee?",
        )
        assert len({k_a, k_b, k_model, k_prompt}) == 4

        db.set_cached_answer(k_a, "doc1", "sess-a", "GroqService", "openai/gpt-oss-120b", {"answer": "ok"}, ttl_seconds=3600)
        assert db.get_cached_answer(k_a) == {"answer": "ok"}
        assert db.get_cached_answer(k_b) is None
        assert db.get_cached_answer(k_model) is None
        assert db.get_cached_answer(k_prompt) is None

        db.delete_document("doc1", session_id="sess-a")
        assert db.get_cached_answer(k_a) is None

    def test_cleanup_expired_documents_protects_active_uploads(self, tmp_path):
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        expired_file = upload_dir / "old_doc.pdf"
        active_file = upload_dir / "active_doc.pdf"
        fresh_file = upload_dir / "new_doc.pdf"
        expired_file.write_bytes(b"%PDF-1.4 old")
        active_file.write_bytes(b"%PDF-1.4 active")
        fresh_file.write_bytes(b"%PDF-1.4 new")

        db = MetadataStore(str(tmp_path / "test.db"))
        db.add_document("old_doc", "old.pdf", str(expired_file), 1, "english", session_id="s1")
        db.add_document("active_doc", "active.pdf", str(active_file), 1, "nepali", session_id="s1")
        db.add_document("new_doc", "new.pdf", str(fresh_file), 1, "nepali", session_id="s1")
        db.set_cached_answer("ck_old", "old_doc", "s1", "GroqService", "m", {"answer": "old"}, ttl_seconds=3600)

        old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        conn = db._get_connection()
        conn.execute("UPDATE documents SET last_accessed_at=? WHERE doc_id IN ('old_doc', 'active_doc')", (old_ts,))
        conn.commit()
        conn.close()

        vs = MagicMock()
        removed = backend_main.cleanup_expired_documents(
            db, vs, upload_dir, retention_seconds=86400, protected_doc_ids={"active_doc"}
        )
        assert removed == 1
        vs.remove_document.assert_called_once_with("old_doc")
        assert not expired_file.exists()
        assert active_file.exists()
        assert fresh_file.exists()
        assert db.get_document("old_doc") is None
        assert db.get_cached_answer("ck_old") is None
        assert db.get_document("active_doc") is not None
        assert db.get_document("new_doc") is not None


class TestGeneral429NoFabricatedFallback:
    def test_ask_general_429_returns_empty_fallback_excerpts(self):
        orig_ollama = getattr(backend_main.app.state, "ollama", None)
        orig_okf = getattr(backend_main.app.state, "okf", None)
        try:
            mock_llm = MagicMock()
            mock_llm.generate.side_effect = LLMRateLimitError("429", retry_after=25)
            mock_okf = MagicMock()
            mock_concept = MagicMock()
            mock_concept.concept_id = "citizenship"
            mock_okf.get_relevant_concepts.return_value = [mock_concept]
            mock_okf.get_context_for_llm.return_value = "OKF curated context"
            backend_main.app.state.ollama = mock_llm
            backend_main.app.state.okf = mock_okf

            resp = asyncio.run(backend_main.ask_general_question(question="What is citizenship?", language="english"))
            assert resp.status_code == 429
            assert resp.headers.get("Retry-After") == "25"
            import json
            body = json.loads(resp.body.decode("utf-8"))
            assert body["verification_status"] == "rate_limited"
            assert body["fallback_excerpts"] == []
        finally:
            backend_main.app.state.ollama = orig_ollama
            backend_main.app.state.okf = orig_okf

    def test_global_rate_limit_handler_returns_429_not_503(self):
        from starlette.requests import Request
        req = Request({"type": "http", "method": "POST", "path": "/explain", "headers": []})
        resp = asyncio.run(backend_main.llm_rate_limit_handler(req, LLMRateLimitError("429", retry_after=19)))
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") == "19"
        import json
        body = json.loads(resp.body.decode("utf-8"))
        assert body["verification_status"] == "rate_limited"
        assert body["fallback_excerpts"] == []
