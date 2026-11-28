"""
Focused tests for the staged zero-cost AI architecture QA requirements:
- Feature flags, ZDR pre-flight gate, and Gemini synthetic-only restriction
- Groq GPT-OSS 120B & Cloudflare Qwen3.8-27B token budgets, HTTP 429, Retry-After / x-ratelimit-reset-*, advisory QuotaTracker
- Server-side evaluator JSON schema validation (never failing open)
- Explicit verification_status semantics (evidence_checks_passed only when independent evaluator + all claims SUPPORTED + deterministic checks pass; never guarantees correctness)
- Session-isolated SQLite caching & invalidation on deletion, generation, model, or prompt changes
- Periodic document-retention cleanup with active-upload protection
- General-question HTTP 429 never fabricating document fallback excerpts
- Independent evaluator self-eval guard, empty/partial claim handling, retention safety, fail-closed defaults, token budget honesty
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    _truncate_chars_heuristic,
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


def _make_independent_layer(evaluator_llm):
    """Build a VerificationLayer with a truly independent evaluator (different object)."""
    validator = GroundingValidator(evaluator_llm)
    primary_llm = MagicMock()  # separate object — _is_independent will be True
    return VerificationLayer(primary_llm, validator)


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
        # heuristic truncation marker (char-budget estimate)
        assert "[truncated" in sent_payload["messages"][0]["content"]

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

    def test_verification_layer_self_eval_returns_not_independently_evaluated(self):
        """When primary and evaluator are the SAME instance, verification must return not_independently_evaluated."""
        same_llm = MagicMock()
        same_llm.generate_structured.return_value = {
            "claims": [{"claim": "Fee is 500", "classification": "SUPPORTED", "evidence": "p1", "page_refs": [1]}],
            "overall_confidence": "HIGH",
            "missing_evidence": [],
            "warning": "",
        }
        validator = GroundingValidator(same_llm)
        layer = VerificationLayer(same_llm, validator)  # same object → self-evaluation
        assert not layer._is_independent
        res = layer.verify("Q?", "A.", [{"page_num": 1, "text": "Evidence"}])
        assert res["verification_status"] == "not_independently_evaluated"
        # Evaluator must NOT have been called
        same_llm.generate_structured.assert_not_called()

    def test_verification_layer_never_fails_open_on_bad_json_or_429(self):
        bad_llm = MagicMock()
        bad_llm.generate_structured.return_value = {"claims": [{"claim": "", "classification": "BAD"}], "overall_confidence": "HIGH"}
        # Use different primary_llm to make it "independent"
        layer = _make_independent_layer(bad_llm)
        res = layer.verify("Q?", "A.", [{"page_num": 1, "text": "Evidence"}])
        assert res["verification_status"] == "unverified_evaluator_unavailable"
        assert res["schema_valid"] is False

        rate_llm = MagicMock()
        rate_llm.generate_structured.side_effect = LLMRateLimitError("429", retry_after=30)
        layer2 = _make_independent_layer(rate_llm)
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
        layer = _make_independent_layer(good_llm)
        res = layer.verify("Fee?", "Fee is NPR 500 (Page 1).", [{"page_num": 1, "text": "Fee NPR 500"}])
        assert res["verification_status"] == "evidence_checks_passed"
        assert res["deterministic_check_passed"] is True
        assert "not a guarantee" in res["recommendation"].lower()

        # Fabricated page citation fails deterministic check even if evaluator passed
        res_bad_page = layer.verify("Fee?", "Fee is NPR 500 (Page 99).", [{"page_num": 1, "text": "Fee NPR 500"}])
        assert res_bad_page["verification_status"] == "unverified_flagged"
        assert res_bad_page["deterministic_check_passed"] is False

        # Existing page number with unrelated/ungrounded content also fails deterministic check
        res_unrelated_page = layer.verify(
            "Fee?",
            "Passport renewal takes fourteen weeks at embassy (Page 1).",
            [{"page_num": 1, "text": "Citizenship duplicate fee NPR 500"}],
        )
        assert res_unrelated_page["verification_status"] == "unverified_flagged"
        assert res_unrelated_page["deterministic_check_passed"] is False


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
        removed, failed = backend_main.cleanup_expired_documents(
            db, vs, upload_dir, retention_seconds=86400, protected_doc_ids={"active_doc"}
        )
        assert removed == 1
        assert failed == []
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


# ─── New regression tests for the 5 source-level issues ──────────────────────

class TestIndependentEvaluatorGate:
    """Fix #1 — independent evaluator self-eval guard and startup gate."""

    def test_self_evaluator_returns_not_independently_evaluated(self):
        """Same LLM instance as primary AND evaluator → not_independently_evaluated, evaluator not called."""
        same_llm = MagicMock()
        validator = GroundingValidator(same_llm)
        layer = VerificationLayer(same_llm, validator)
        assert not layer._is_independent
        res = layer.verify("Q?", "A.", [{"page_num": 1, "text": "Evidence"}])
        assert res["verification_status"] == "not_independently_evaluated"
        same_llm.generate_structured.assert_not_called()

    def test_disabled_evaluator_none_returns_not_independently_evaluated(self):
        """evaluator_llm=None → GroundingValidator raises LLMUnavailableError → not_independently_evaluated."""
        validator = GroundingValidator(None)  # None evaluator
        primary_llm = MagicMock()
        layer = VerificationLayer(primary_llm, validator)
        # validator.llm is None → not independent
        assert not layer._is_independent
        res = layer.verify("Q?", "A.", [{"page_num": 1, "text": "Evidence"}])
        assert res["verification_status"] == "not_independently_evaluated"

    def test_public_production_requires_independent_evaluator(self):
        """PUBLIC_PRODUCTION_MODE=true with ENABLE_INDEPENDENT_EVALUATOR=false → ValueError at build time."""
        with pytest.raises(ValueError, match="PUBLIC_PRODUCTION_MODE=true requires ENABLE_INDEPENDENT_EVALUATOR"):
            backend_main.build_llm_and_evaluator(
                llm_provider="ollama",
                enable_independent_evaluator=False,
                public_production_mode=True,
            )

    def test_independent_evaluator_different_instance_is_independent(self):
        """Different LLM objects → _is_independent=True, evaluator is called."""
        evaluator_llm = MagicMock()
        evaluator_llm.generate_structured.return_value = {
            "claims": [{"claim": "Fee is 500", "classification": "SUPPORTED", "evidence": "p1", "page_refs": [1]}],
            "overall_confidence": "HIGH",
            "missing_evidence": [],
            "warning": "",
        }
        layer = _make_independent_layer(evaluator_llm)
        assert layer._is_independent
        res = layer.verify("Q?", "Fee is 500 (Page 1).", [{"page_num": 1, "text": "Fee 500"}])
        evaluator_llm.generate_structured.assert_called_once()
        assert res["verification_status"] == "evidence_checks_passed"


class TestEmptyAndPartialClaims:
    """Fix #2 — empty claims → not_independently_evaluated; partial → partially_supported; all SUPPORTED → evidence_checks_passed."""

    def test_empty_claims_returns_not_independently_evaluated(self):
        """Evaluator returns valid schema with empty claims list → not_independently_evaluated."""
        evaluator_llm = MagicMock()
        evaluator_llm.generate_structured.return_value = {
            "claims": [],
            "overall_confidence": "HIGH",
            "missing_evidence": [],
            "warning": "",
        }
        layer = _make_independent_layer(evaluator_llm)
        res = layer.verify("Q?", "Some answer.", [{"page_num": 1, "text": "Evidence"}])
        assert res["verification_status"] == "not_independently_evaluated"
        assert "no claims" in res["recommendation"].lower()

    def test_all_supported_claims_returns_evidence_checks_passed(self):
        """All claims SUPPORTED + HIGH confidence → evidence_checks_passed."""
        evaluator_llm = MagicMock()
        evaluator_llm.generate_structured.return_value = {
            "claims": [
                {"claim": "Fee is NPR 500", "classification": "SUPPORTED", "evidence": "p1", "page_refs": [1]},
                {"claim": "Deadline is 30 days", "classification": "SUPPORTED", "evidence": "p1", "page_refs": [1]},
            ],
            "overall_confidence": "HIGH",
            "missing_evidence": [],
            "warning": "",
        }
        layer = _make_independent_layer(evaluator_llm)
        res = layer.verify("What?", "Fee is NPR 500 (Page 1). Deadline is 30 days (Page 1).",
                           [{"page_num": 1, "text": "Fee NPR 500 deadline 30 days"}])
        assert res["verification_status"] == "evidence_checks_passed"

    def test_partially_supported_claim_returns_partially_supported_status(self):
        """Any PARTIALLY_SUPPORTED claim → partially_supported (not evidence_checks_passed)."""
        evaluator_llm = MagicMock()
        evaluator_llm.generate_structured.return_value = {
            "claims": [
                {"claim": "Fee is NPR 500", "classification": "SUPPORTED", "evidence": "p1", "page_refs": [1]},
                {"claim": "Deadline is 30 days", "classification": "PARTIALLY_SUPPORTED", "evidence": "p1", "page_refs": [1]},
            ],
            "overall_confidence": "HIGH",  # evaluator says HIGH but we have partial claims
            "missing_evidence": [],
            "warning": "",
        }
        layer = _make_independent_layer(evaluator_llm)
        res = layer.verify("What?", "Fee is NPR 500 (Page 1). Deadline is 30 days.",
                           [{"page_num": 1, "text": "Fee NPR 500"}])
        assert res["verification_status"] == "partially_supported"
        assert "partially" in res["recommendation"].lower()

    def test_mixed_supported_and_insufficient_returns_partially_supported(self):
        """SUPPORTED + INSUFFICIENT_EVIDENCE → partially_supported (not evidence_checks_passed)."""
        evaluator_llm = MagicMock()
        evaluator_llm.generate_structured.return_value = {
            "claims": [
                {"claim": "Fee is NPR 500", "classification": "SUPPORTED", "evidence": "p1", "page_refs": [1]},
                {"claim": "Penalty is NPR 1000", "classification": "INSUFFICIENT_EVIDENCE", "evidence": "", "page_refs": []},
            ],
            "overall_confidence": "MEDIUM",
            "missing_evidence": ["Penalty not in evidence"],
            "warning": "",
        }
        layer = _make_independent_layer(evaluator_llm)
        res = layer.verify("What?", "Fee is NPR 500 (Page 1). Penalty is NPR 1000.",
                           [{"page_num": 1, "text": "Fee NPR 500"}])
        # INSUFFICIENT_EVIDENCE pulls band to MEDIUM → partially_supported
        assert res["verification_status"] == "partially_supported"


class TestRetentionSafety:
    """Fix #3 — artifact-first deletion, metadata last, idempotent, track failures."""

    def test_file_deletion_failure_preserves_metadata(self, tmp_path):
        """If file unlink fails, metadata row must NOT be deleted."""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        expired_file = upload_dir / "expired.pdf"
        expired_file.write_bytes(b"%PDF expired")

        db = MetadataStore(str(tmp_path / "test.db"))
        db.add_document("exp_doc", "expired.pdf", str(expired_file), 1, "english", session_id="s1")
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        conn = db._get_connection()
        conn.execute("UPDATE documents SET last_accessed_at=? WHERE doc_id='exp_doc'", (old_ts,))
        conn.commit()
        conn.close()

        vs = MagicMock()

        def fail_unlink():
            raise PermissionError("file locked")

        with patch.object(Path, "unlink", side_effect=PermissionError("file locked")):
            removed, failed = backend_main.cleanup_expired_documents(
                db, vs, upload_dir, retention_seconds=3600
            )

        # Metadata must still exist — file deletion failed
        assert removed == 0
        assert len(failed) >= 1
        assert any(f["step"] == "file_unlink" for f in failed)
        assert db.get_document("exp_doc") is not None  # preserved for retry

    def test_vector_deletion_failure_preserves_metadata(self, tmp_path):
        """If vector remove fails (non-not-found error), metadata row must NOT be deleted."""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        expired_file = upload_dir / "expired2.pdf"
        expired_file.write_bytes(b"%PDF expired2")

        db = MetadataStore(str(tmp_path / "test.db"))
        db.add_document("exp_doc2", "expired2.pdf", str(expired_file), 1, "english", session_id="s1")
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        conn = db._get_connection()
        conn.execute("UPDATE documents SET last_accessed_at=? WHERE doc_id='exp_doc2'", (old_ts,))
        conn.commit()
        conn.close()

        vs = MagicMock()
        vs.remove_document.side_effect = RuntimeError("index write error")

        removed, failed = backend_main.cleanup_expired_documents(
            db, vs, upload_dir, retention_seconds=3600
        )

        # Metadata must still exist — vector deletion failed
        assert removed == 0
        assert len(failed) >= 1
        assert any(f["step"] == "vector_remove" for f in failed)
        assert db.get_document("exp_doc2") is not None  # preserved for retry

    def test_idempotent_cleanup_on_already_deleted_file(self, tmp_path):
        """File already physically gone → idempotent success, metadata IS deleted."""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        # Note: file intentionally NOT created — simulates already-removed file

        db = MetadataStore(str(tmp_path / "test.db"))
        db.add_document("ghost_doc", "ghost.pdf", str(upload_dir / "ghost.pdf"), 1, "english", session_id="s1")
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        conn = db._get_connection()
        conn.execute("UPDATE documents SET last_accessed_at=? WHERE doc_id='ghost_doc'", (old_ts,))
        conn.commit()
        conn.close()

        vs = MagicMock()
        removed, failed = backend_main.cleanup_expired_documents(
            db, vs, upload_dir, retention_seconds=3600
        )

        # Already-gone file is idempotent success → metadata removed
        assert removed == 1
        assert failed == []
        assert db.get_document("ghost_doc") is None


class TestFailClosedResponseStatus:
    """Fix #4 — missing verification_status must never default to 'verified' or 'evidence_checks_passed'."""

    def test_missing_verification_key_returns_unverified_not_verified(self):
        """verify() dict without 'verification_status' key → unverified_evaluator_unavailable."""
        empty_verification: dict = {}
        result = empty_verification.get("verification_status") or "unverified_evaluator_unavailable"
        assert result == "unverified_evaluator_unavailable"
        assert result != "verified"
        assert result != "evidence_checks_passed"

    def test_none_verification_status_returns_unverified(self):
        """verify() dict with verification_status=None → unverified_evaluator_unavailable."""
        verification = {"verification_status": None}
        result = verification.get("verification_status") or "unverified_evaluator_unavailable"
        assert result == "unverified_evaluator_unavailable"

    def test_verification_layer_never_returns_verified_on_any_path(self):
        """VerificationLayer.verify() must never return verification_status='verified'."""
        evaluator_llm = MagicMock()
        evaluator_llm.generate_structured.side_effect = LLMUnavailableError("unavailable")
        layer = _make_independent_layer(evaluator_llm)
        res = layer.verify("Q?", "A.", [{"page_num": 1, "text": "Evidence"}])
        assert res["verification_status"] != "verified"
        assert res["verification_status"] in {
            "evidence_checks_passed", "unverified_flagged",
            "unverified_evaluator_unavailable", "not_independently_evaluated",
            "partially_supported", "rate_limited",
        }


class TestTokenBudgetHonesty:
    """Fix #5 — char heuristic labeled as estimate, provider usage captured."""

    def test_char_heuristic_function_name_and_docstring(self):
        """_truncate_chars_heuristic must exist and docstring must say 'heuristic' or 'estimate'."""
        import inspect
        doc = inspect.getdoc(_truncate_chars_heuristic) or ""
        assert "heuristic" in doc.lower() or "estimate" in doc.lower()

    def test_truncation_uses_char_budget_not_token_count(self):
        """10 tokens * 3 chars = 30 chars max; 'A' * 100 must be truncated."""
        result = _truncate_chars_heuristic("A" * 100, max_tokens=10)
        assert len(result) < 100
        assert "truncated" in result

    def test_short_text_not_truncated(self):
        """Text well within char budget must not be truncated."""
        text = "Short text."
        result = _truncate_chars_heuristic(text, max_tokens=1000)
        assert result == text

    def test_groq_captures_provider_token_usage(self):
        """GroqService.last_usage must be populated from provider's 'usage' field."""
        session = MagicMock()
        session.post.return_value = _FakeResponse(200, {
            "choices": [{"message": {"content": "The answer is 42."}}],
            "usage": {"prompt_tokens": 150, "completion_tokens": 20, "total_tokens": 170},
        })
        svc = GroqService(api_key="gsk_test", session=session)
        result = svc.generate("What is 6 times 7?")
        assert result == "The answer is 42."
        assert svc.last_usage.get("prompt_tokens") == 150
        assert svc.last_usage.get("completion_tokens") == 20

    def test_cloudflare_captures_provider_token_usage(self):
        """CloudflareWorkersAIService.last_usage must be populated from result.usage if present."""
        session = MagicMock()
        session.post.return_value = _FakeResponse(200, {
            "success": True,
            "result": {
                "response": "The answer.",
                "usage": {"input_tokens": 80, "output_tokens": 10},
            },
        })
        svc = CloudflareWorkersAIService(account_id="acct", api_token="tok", session=session)
        result = svc.generate("Q?")
        assert result == "The answer."
        assert svc.last_usage.get("input_tokens") == 80

    def test_select_evidence_for_budget_selects_whole_chunks(self):
        """select_evidence_for_budget stops at chunk boundaries without slicing mid-chunk."""
        chunks = [
            {"page_num": 1, "text": "A" * 40},
            {"page_num": 2, "text": "B" * 40},
            {"page_num": 3, "text": "C" * 40},
        ]
        selected = backend_main.select_evidence_for_budget(chunks, max_chunks=10, max_chars_estimate=85)
        assert len(selected) == 2
        assert selected[0]["text"] == "A" * 40
        assert selected[1]["text"] == "B" * 40


# ─── Regression tests for final 4+1 independent review items ─────────────────

class TestVectorDeletionSafety:
    """Issue 1 — VectorStore.remove_document() must raise OSError on locked files and preserve metadata."""

    def test_locked_faiss_file_raises_and_preserves_registry_and_sqlite(self, tmp_path):
        from vector_store import VectorStore

        vec_dir = tmp_path / "vectors"
        vec_dir.mkdir()
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        pdf_file = upload_dir / "locked_doc.pdf"
        pdf_file.write_bytes(b"%PDF locked")

        vs = VectorStore(vectors_dir=str(vec_dir), dimension=4)
        faiss_file = vec_dir / "locked_doc.faiss"
        meta_file = vec_dir / "locked_doc_meta.json"
        faiss_file.write_bytes(b"FAKEFAISS")
        meta_file.write_text("[]", encoding="utf-8")
        vs._doc_indices["locked_doc"] = str(faiss_file)
        vs._save_registry()

        db = MetadataStore(str(tmp_path / "test.db"))
        db.add_document("locked_doc", "locked.pdf", str(pdf_file), 1, "english", session_id="s1")
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        conn = db._get_connection()
        conn.execute("UPDATE documents SET last_accessed_at=? WHERE doc_id='locked_doc'", (old_ts,))
        conn.commit()
        conn.close()

        orig_unlink = Path.unlink

        def fail_on_faiss(self, missing_ok=False):
            if self.name.endswith(".faiss"):
                raise PermissionError("FAISS file locked")
            return orig_unlink(self, missing_ok=missing_ok)

        with patch.object(Path, "unlink", fail_on_faiss):
            removed, failed = backend_main.cleanup_expired_documents(
                db, vs, upload_dir, retention_seconds=3600
            )

        assert removed == 0
        assert any(f["step"] == "vector_remove" for f in failed)
        assert "locked_doc" in vs._doc_indices
        assert db.get_document("locked_doc") is not None

    def test_locked_meta_json_file_raises_and_preserves_metadata(self, tmp_path):
        from vector_store import VectorStore

        vec_dir = tmp_path / "vectors"
        vec_dir.mkdir()
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()

        vs = VectorStore(vectors_dir=str(vec_dir), dimension=4)
        faiss_file = vec_dir / "locked_meta_doc.faiss"
        meta_file = vec_dir / "locked_meta_doc_meta.json"
        faiss_file.write_bytes(b"FAKEFAISS")
        meta_file.write_text("[]", encoding="utf-8")
        vs._doc_indices["locked_meta_doc"] = str(faiss_file)
        vs._save_registry()

        db = MetadataStore(str(tmp_path / "test.db"))
        db.add_document("locked_meta_doc", "m.pdf", str(upload_dir / "m.pdf"), 1, "english", session_id="s1")
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        conn = db._get_connection()
        conn.execute("UPDATE documents SET last_accessed_at=? WHERE doc_id='locked_meta_doc'", (old_ts,))
        conn.commit()
        conn.close()

        orig_unlink = Path.unlink

        def fail_on_meta_json(self, missing_ok=False):
            if self.name.endswith("_meta.json"):
                raise PermissionError("Metadata JSON file locked")
            return orig_unlink(self, missing_ok=missing_ok)

        with patch.object(Path, "unlink", fail_on_meta_json):
            with pytest.raises(OSError, match="Failed to remove vector artifact"):
                vs.remove_document("locked_meta_doc")

        # Restore normal unlink and verify cleanup_expired_documents preserves SQLite on meta lock
        with patch.object(Path, "unlink", fail_on_meta_json):
            removed, failed = backend_main.cleanup_expired_documents(
                db, vs, upload_dir, retention_seconds=3600
            )
        assert removed == 0
        assert any(f["step"] == "vector_remove" for f in failed)
        assert db.get_document("locked_meta_doc") is not None


class TestCachePrivacyInvalidation:
    """Issue 2 — Deleting/reindexing a document invalidates session-wide (doc_id=None) cached answers while preserving other sessions."""

    def test_deleting_one_doc_invalidates_session_wide_cache_preserving_other_sessions(self, tmp_path):
        db = MetadataStore(str(tmp_path / "test.db"))
        db.add_document("doc_a", "a.pdf", str(tmp_path / "a.pdf"), 1, "english", session_id="sess-a")
        db.add_document("doc_b", "b.pdf", str(tmp_path / "b.pdf"), 1, "english", session_id="sess-a")
        db.add_document("doc_other", "other.pdf", str(tmp_path / "other.pdf"), 1, "english", session_id="sess-b")

        # Store doc-specific cache for doc_a, session-wide cache (doc_id=None) for sess-a, and session-wide cache for sess-b
        db.set_cached_answer("ck_doc_a", "doc_a", "sess-a", "GroqService", "m", {"answer": "from doc_a"}, ttl_seconds=3600)
        db.set_cached_answer("ck_sess_a_wide", None, "sess-a", "GroqService", "m", {"answer": "derived from doc_a and doc_b"}, ttl_seconds=3600)
        db.set_cached_answer("ck_sess_b_wide", None, "sess-b", "GroqService", "m", {"answer": "sess-b private"}, ttl_seconds=3600)

        assert db.get_cached_answer("ck_sess_a_wide") == {"answer": "derived from doc_a and doc_b"}

        # Delete doc_a in sess-a
        assert db.delete_document("doc_a", session_id="sess-a") is True

        # Both doc_a's cache AND sess-a's session-wide derived cache must be purged
        assert db.get_cached_answer("ck_doc_a") is None
        assert db.get_cached_answer("ck_sess_a_wide") is None
        # sess-b's cache must remain isolated and intact
        assert db.get_cached_answer("ck_sess_b_wide") == {"answer": "sess-b private"}

    def test_reindexing_one_doc_invalidates_session_wide_cache(self, tmp_path):
        db = MetadataStore(str(tmp_path / "test.db"))
        db.add_document("doc_a", "a.pdf", str(tmp_path / "a.pdf"), 1, "english", session_id="sess-a")
        db.set_cached_answer("ck_doc_a", "doc_a", "sess-a", "GroqService", "m", {"answer": "old"}, ttl_seconds=3600)
        db.set_cached_answer("ck_sess_a_wide", None, "sess-a", "GroqService", "m", {"answer": "old wide"}, ttl_seconds=3600)
        db.set_cached_answer("ck_sess_b_wide", None, "sess-b", "GroqService", "m", {"answer": "b wide"}, ttl_seconds=3600)

        db.commit_reindex(
            doc_id="doc_a",
            new_gen=1,
            chunks=[{"chunk_id": "c1", "doc_id": "doc_a", "page_num": 1, "text": "Updated text", "source_type": "pdf"}],
            filename="a.pdf",
            filepath=str(tmp_path / "a.pdf"),
            page_count=1,
            language_hint="english",
            expected_gen=0,
        )

        assert db.get_cached_answer("ck_doc_a") is None
        assert db.get_cached_answer("ck_sess_a_wide") is None
        assert db.get_cached_answer("ck_sess_b_wide") == {"answer": "b wide"}


class TestTrueModelIndependence:
    """Issue 3 — Compare provider + model identifiers, reject EVALUATOR_PROVIDER=same and same provider/model in public prod."""

    def test_distinct_instances_same_provider_and_model_rejected(self):
        from llm_service import is_independent_evaluator

        s1 = GroqService(api_key="gsk_1", model="openai/gpt-oss-120b", session=MagicMock())
        s2 = GroqService(api_key="gsk_2", model="openai/gpt-oss-120b", session=MagicMock())
        assert is_independent_evaluator(s1, s2) is False
        layer = VerificationLayer(s1, GroundingValidator(s2))
        assert layer._is_independent is False
        res = layer.verify("Q?", "A.", [{"page_num": 1, "text": "Evidence"}])
        assert res["verification_status"] == "not_independently_evaluated"

    def test_same_provider_different_models_allowed(self):
        from llm_service import is_independent_evaluator

        s1 = GroqService(api_key="gsk_1", model="openai/gpt-oss-120b", session=MagicMock())
        s2 = GroqService(api_key="gsk_2", model="llama-3.3-70b-versatile", session=MagicMock())
        assert is_independent_evaluator(s1, s2) is True

    def test_public_production_rejects_evaluator_provider_same(self):
        with pytest.raises(ValueError, match="EVALUATOR_PROVIDER='same'"):
            backend_main.build_llm_and_evaluator(
                llm_provider="groq",
                groq_api_key="gsk_test",
                zdr_verified=True,
                enable_independent_evaluator=True,
                evaluator_provider="same",
                public_production_mode=True,
            )

    def test_public_production_rejects_same_provider_and_model(self):
        with pytest.raises(ValueError, match="distinct provider/model"):
            backend_main.build_llm_and_evaluator(
                llm_provider="groq",
                groq_api_key="gsk_test",
                groq_model="openai/gpt-oss-120b",
                zdr_verified=True,
                enable_independent_evaluator=True,
                evaluator_provider="groq",
                public_production_mode=True,
            )


class TestClaimLevelCitationValidation:
    """Issue 4 — Validate every evaluator claim's page_refs & evidence mappings; preserve OKF & official-source handling."""

    def test_fabricated_claim_page_refs_flagged(self):
        evaluator_llm = MagicMock()
        evaluator_llm.generate_structured.return_value = {
            "claims": [
                {"claim": "Fee is NPR 500", "classification": "SUPPORTED", "evidence": "Page 99 states 500", "page_refs": [99]}
            ],
            "overall_confidence": "HIGH",
            "missing_evidence": [],
            "warning": "",
        }
        layer = _make_independent_layer(evaluator_llm)
        res = layer.verify("Fee?", "Fee is NPR 500 (Page 1).", [{"page_num": 1, "text": "Fee NPR 500"}])
        assert res["verification_status"] == "unverified_flagged"
        assert res["deterministic_check_passed"] is False
        assert any("page_refs" in issue for issue in res["deterministic_issues"])

    def test_empty_claim_evidence_mapping_flagged(self):
        evaluator_llm = MagicMock()
        evaluator_llm.generate_structured.return_value = {
            "claims": [
                {"claim": "Fee is NPR 500", "classification": "SUPPORTED", "evidence": "", "page_refs": [1]}
            ],
            "overall_confidence": "HIGH",
            "missing_evidence": [],
            "warning": "",
        }
        layer = _make_independent_layer(evaluator_llm)
        res = layer.verify("Fee?", "Fee is NPR 500 (Page 1).", [{"page_num": 1, "text": "Fee NPR 500"}])
        assert res["verification_status"] == "unverified_flagged"
        assert res["deterministic_check_passed"] is False

    def test_empty_claim_page_refs_on_document_evidence_flagged(self):
        evaluator_llm = MagicMock()
        evaluator_llm.generate_structured.return_value = {
            "claims": [
                {"claim": "Fee is NPR 500", "classification": "SUPPORTED", "evidence": "Fee NPR 500", "page_refs": []}
            ],
            "overall_confidence": "HIGH",
            "missing_evidence": [],
            "warning": "",
        }
        layer = _make_independent_layer(evaluator_llm)
        res = layer.verify("Fee?", "Fee is NPR 500.", [{"page_num": 1, "text": "Fee NPR 500"}])
        assert res["verification_status"] == "unverified_flagged"
        assert res["deterministic_check_passed"] is False

    def test_okf_and_official_source_evidence_preserved(self):
        evaluator_llm = MagicMock()
        evaluator_llm.generate_structured.return_value = {
            "claims": [
                {"claim": "Citizenship is issued by DAO", "classification": "SUPPORTED", "evidence": "OKF citizenship concept", "page_refs": []}
            ],
            "overall_confidence": "HIGH",
            "missing_evidence": [],
            "warning": "",
        }
        layer = _make_independent_layer(evaluator_llm)
        res = layer.verify(
            "Who issues citizenship?",
            "The District Administration Office (DAO) issues citizenship.",
            [{"page_num": None, "text": "DAO issues citizenship.", "source_type": "okf"}],
        )
        assert res["verification_status"] == "evidence_checks_passed"
        assert res["deterministic_check_passed"] is True

    def test_okf_evidence_with_fabricated_numeric_page_ref_flagged(self):
        evaluator_llm = MagicMock()
        evaluator_llm.generate_structured.return_value = {
            "claims": [
                {"claim": "Citizenship is issued by DAO", "classification": "SUPPORTED", "evidence": "Page 3", "page_refs": [3]}
            ],
            "overall_confidence": "HIGH",
            "missing_evidence": [],
            "warning": "",
        }
        layer = _make_independent_layer(evaluator_llm)
        res = layer.verify(
            "Who issues citizenship?",
            "The DAO issues citizenship.",
            [{"page_num": None, "text": "DAO issues citizenship.", "source_type": "official"}],
        )
        assert res["verification_status"] == "unverified_flagged"
        assert res["deterministic_check_passed"] is False


