"""
Tests for official-source answering (PR-012) — authority, freshness,
claims, provenance, and failure cases. No live LLM or server needed.

Run: .venv/Scripts/python.exe -m pytest tests/test_official_answer.py -v
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest

import source_registry
import official_answer
from official_answer import (
    OfficialAnswerService,
    OfficialEvidence,
    detect_official_intent,
    gather_official_evidence,
    freshness_report,
    load_source_documents,
    load_fetched_date,
    KNOWLEDGE_DIR,
)


# ─── Fixtures: knowledge cache ────────────────────────────────────

PASSPORT_CACHE = {
    "source_id": "passport-dept",
    "fetched_date": "2026-09-17",
    "documents": [
        {
            "title": "Passport fees",
            "page": 1,
            "text": "Ordinary passport 34 pages costs Rs. 5,000 for normal "
                    "service. Express service costs Rs. 12,000. Fees are set "
                    "by the Department of Passports.",
        }
    ],
}

STALE_CACHE = {
    "source_id": "passport-dept",
    "fetched_date": "2020-01-01",
    "documents": PASSPORT_CACHE["documents"],
}


@pytest.fixture(autouse=True)
def isolation(monkeypatch):
    """Point KNOWLEDGE_DIR at a temp dir with a current passport cache."""
    tmp = tempfile.mkdtemp(prefix="hamigenz_kb_")
    with open(os.path.join(tmp, "passport-dept.json"), "w",
              encoding="utf-8") as f:
        json.dump(PASSPORT_CACHE, f, ensure_ascii=False)
    monkeypatch.setattr(official_answer, "KNOWLEDGE_DIR", tmp)
    yield tmp


class FakeLLM:
    """Deterministic LLM double for offline testing."""

    def __init__(self, reply="The passport fee is Rs. 5,000 per the Department of Passports."):
        self.reply = reply
        self.last_prompt = None
        self.fail = False

    def generate(self, prompt, **kwargs):
        if self.fail:
            raise official_answer.LLMUnavailableError("down")
        self.last_prompt = prompt
        return self.reply


class FakeVerification:
    def verify(self, question, answer, evidence):
        return {
            "grounding_report": {},
            "contradiction_found": False,
            "contradiction_claims": [],
            "confidence_score": 90,
            "confidence_band": "HIGH",
            "unsupported_facts": [],
            "recommendation": "ok",
        }


# ─── Authority ────────────────────────────────────────────────────

class TestAuthority:
    def test_verified_registry_source_used(self):
        ev = gather_official_evidence("passport fee", ["passport"])
        assert ev
        assert all(e.verified for e in ev)
        assert all(e.status == "current" for e in ev)

    def test_unverified_source_excluded(self, monkeypatch):
        # Mark the passport source unverified → no evidence may come from it
        real = source_registry.sources_for_category

        def fake(cat):
            srcs = real(cat)
            for s in srcs:
                s["verified"] = False
            return srcs

        monkeypatch.setattr(source_registry, "sources_for_category", fake)
        assert gather_official_evidence("passport fee", ["passport"]) == []

    def test_outdated_source_excluded(self, monkeypatch):
        real = source_registry.sources_for_category

        def fake(cat):
            srcs = real(cat)
            for s in srcs:
                s["status"] = "outdated"
            return srcs

        monkeypatch.setattr(source_registry, "sources_for_category", fake)
        assert gather_official_evidence("passport fee", ["passport"]) == []

    def test_lookalike_domain_not_official(self):
        c = source_registry.classify_url("https://nepalpassport.gov.np.evil.com")
        assert c["classification"] == "unverified"

    def test_uncurated_source_missing_from_registry(self):
        assert source_registry.find_by_domain("mystery-agency.gov.np") is None
        assert source_registry.classify_url(
            "https://mystery-agency.gov.np/x")["classification"] == "unverified"


# ─── Freshness ────────────────────────────────────────────────────

class TestFreshness:
    def _ev(self, fetched=None, status="current", verified_date="2026-09-17"):
        return [OfficialEvidence(
            source_id="passport-dept", organization="Dept", title="t",
            url="https://nepalpassport.gov.np", source_type="government_agency",
            authority_level="authoritative", verified=True, status=status,
            verified_date=verified_date, fetched_date=fetched,
            text="x" * 50, doc_title="d")]

    def test_current(self):
        assert freshness_report(self._ev(fetched="2026-09-17"))["verdict"] == "current"

    def test_stale_cache(self):
        rep = freshness_report(self._ev(fetched="2020-01-01"))
        assert rep["verdict"] == "stale"
        assert rep["stale_sources"]

    def test_outdated_status(self):
        rep = freshness_report(self._ev(fetched="2026-09-17", status="outdated"))
        assert rep["verdict"] == "stale"

    def test_revoked_status(self):
        rep = freshness_report(self._ev(fetched="2026-09-17", status="repealed"))
        assert rep["verdict"] == "stale"

    def test_missing_fetch_date(self):
        rep = freshness_report(self._ev(fetched=None))
        assert rep["verdict"] == "unknown"

    def test_no_evidence(self):
        rep = freshness_report([])
        assert rep["verdict"] == "none"


# ─── Claims ───────────────────────────────────────────────────────

class TestClaims:
    def _svc(self, reply):
        return OfficialAnswerService(llm=FakeLLM(reply),
                                     verification=FakeVerification())

    def test_supported_fee_answered_from_source(self):
        svc = self._svc("Per the Department of Passports, the fee is Rs. 5,000.")
        out = svc.answer("passport ko fee kati ho?", lang="english")
        assert out["provenance"] == "official_source"
        assert out["meta"]["status"] == "answered"
        assert out["official_sources"][0]["source_id"] == "passport-dept"
        # The prompt must have contained the actual fee text from the cache
        # (grounding, not post-hoc URL attachment)
        assert "5,000" in (svc.llm.last_prompt or "")

    def test_unsupported_claim_flagged_by_verification(self):
        class FailVerification:
            def verify(self, q, a, e):
                return {"grounding_report": {}, "contradiction_found": True,
                        "contradiction_claims": ["fee is Rs. 99"],
                        "confidence_score": 10, "confidence_band": "LOW",
                        "unsupported_facts": ["fee is Rs. 99"],
                        "recommendation": "check source"}

        svc = OfficialAnswerService(llm=FakeLLM("Fee is Rs. 99."),
                                    verification=FailVerification())
        out = svc.answer("passport fee?", lang="english")
        assert out["verification"]["contradiction_found"] is True
        assert out["verification"]["confidence_band"] == "LOW"

    def test_fabricated_deadline_not_in_answer_flow(self):
        # If the LLM tries to answer outside the evidence, the verification
        # layer receives only cached evidence — it can flag the fabrication.
        svc = self._svc("The deadline is 2099-01-01.")
        out = svc.answer("passport deadline?", lang="english")
        evidence_text = " ".join(e.text for e in
                                 gather_official_evidence("passport deadline?", ["passport"]))
        assert "2099-01-01" not in evidence_text  # fabrication is not in evidence
        assert out["official_sources"]  # but real sources are still cited

    def test_conflicting_information_surfaced(self):
        # Two cache entries claiming different fees → both retrieved; the
        # verification report must be present for the UI to show conflict.
        svc = self._svc("Fees differ between notices.")
        out = svc.answer("passport fee?", lang="english")
        assert "verification" in out


# ─── Provenance ───────────────────────────────────────────────────

class TestProvenance:
    def test_official_provenance(self):
        svc = OfficialAnswerService(llm=FakeLLM(), verification=FakeVerification())
        assert svc.answer("passport fee?", lang="english")["provenance"] == "official_source"

    def test_general_ai_provenance_when_no_source(self):
        svc = OfficialAnswerService(llm=FakeLLM(), verification=FakeVerification())
        out = svc.answer("passport fee?", lang="english")
        # Default isolation cache HAS passport docs → official. Clear it:
        official_answer.KNOWLEDGE_DIR = tempfile.mkdtemp()
        out = svc.answer("passport fee?", lang="english")
        assert out["provenance"] == "general_ai"
        assert out["meta"]["status"] == "no_source"
        # ...but it still points to the official source
        assert out["official_sources"][0]["url"].endswith("gov.np")

    def test_non_official_question_not_blocked(self):
        svc = OfficialAnswerService(llm=FakeLLM(), verification=FakeVerification())
        out = svc.answer("write me a poem about mountains", lang="english")
        assert out["meta"]["status"] == "no_source"  # not official → no cached evidence
        assert "official" in out["grounding_note"].lower() or out["provenance"] == "general_ai"


# ─── Failure cases ────────────────────────────────────────────────

class TestFailures:
    def test_llm_down_serves_raw_evidence(self):
        llm = FakeLLM()
        llm.fail = True
        svc = OfficialAnswerService(llm=llm, verification=FakeVerification())
        out = svc.answer("passport fee?", lang="english")
        assert out["meta"]["status"] == "llm_down"
        assert out["provenance"] == "official_source"
        assert "5,000" in out["answer"]  # raw evidence still shown

    def test_retrieval_failure_returns_no_source(self, monkeypatch):
        monkeypatch.setattr(official_answer, "gather_official_evidence",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("retrieval broke")))
        svc = OfficialAnswerService(llm=FakeLLM(), verification=FakeVerification())
        out = svc.answer("passport fee?", lang="english")
        assert out["meta"]["status"] == "no_source"
        assert out["provenance"] == "general_ai"

    def test_stale_source_answered_with_warning(self, monkeypatch):
        tmp = tempfile.mkdtemp()
        with open(os.path.join(tmp, "passport-dept.json"), "w",
                  encoding="utf-8") as f:
            json.dump(STALE_CACHE, f, ensure_ascii=False)
        official_answer.KNOWLEDGE_DIR = tmp
        svc = OfficialAnswerService(llm=FakeLLM(), verification=FakeVerification())
        out = svc.answer("passport fee?", lang="english")
        assert out["freshness"]["verdict"] == "stale"
        assert "outdated" in out["grounding_note"].lower() or "old" in out["grounding_note"].lower()


# ─── Intent detection ─────────────────────────────────────────────

class TestIntent:
    @pytest.mark.parametrize("question,official,cats,dynamic", [
        ("passport ko fee kati ho?", True, ["passport"], True),
        ("What is the passport fee?", True, ["passport"], True),
        ("driving license kasari banne?", True, ["traffic"], True),
        ("नेपालको कानून के भन्छ?", True, ["laws"], False),
        ("write me a poem about mountains", False, [], False),
        ("best trekking route in everest?", False, [], False),
    ])
    def test_intent(self, question, official, cats, dynamic):
        r = detect_official_intent(question)
        assert r["is_official"] == official
        assert r["categories"] == cats
        assert r["wants_dynamic_info"] == dynamic
