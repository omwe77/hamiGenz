"""
Self-consistency tests for the PR-014 evaluation system.

These verify the evaluation machinery itself (dataset integrity,
deterministic scoring, benchmark plumbing) without loading real models.
Run: .venv/Scripts/python.exe -m pytest tests/test_evaluation.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from tests.evaluation.gold_dataset import (
    GOLD_CASES, check_case_facts, GoldCase, normalized)
from tests.evaluation.eval_explanations import (
    detect_script, check_level, run_evaluator, _MockLLM)


class TestGoldDatasetIntegrity:
    """The gold dataset must be internally consistent and human-verifiable."""

    def test_dataset_not_empty(self):
        assert len(GOLD_CASES) >= 14, "need coverage across categories"

    def test_all_categories_covered(self):
        seen = {c.category for c in GOLD_CASES}
        expected = {
            "formal_nepali", "legal_nepali", "negation", "conditions",
            "exceptions", "dates", "fees", "english_to_nepali",
            "terminology", "romanized_nepali", "mixed",
        }
        missing = expected - seen
        assert not missing, f"missing categories: {missing}"

    def test_all_levels_covered(self):
        levels = {c.level for c in GOLD_CASES}
        assert {"original", "simple", "very_simple"} <= levels

    def test_all_language_expectations_covered(self):
        langs = {c.expected_lang for c in GOLD_CASES}
        assert {"nepali", "any"} <= langs

    def test_every_case_has_key_facts(self):
        for c in GOLD_CASES:
            assert c.key_facts, f"{c.case_id} missing key_facts"
            assert c.input_text, f"{c.case_id} missing input_text"
            assert c.notes, (
                f"{c.case_id} missing notes — gold facts must carry a "
                "human-verification rationale")

    def test_key_facts_actually_in_source(self):
        """A key fact that isn't in the input text is a dataset bug."""
        from action_extractor import normalize_digits
        for c in GOLD_CASES:
            src = normalized(c.input_text)
            src_digits = normalized(normalize_digits(c.input_text))
            for fact in c.key_facts:
                alternatives = fact if isinstance(fact, (list, tuple)) else [fact]
                found = any(
                    normalized(a) in src
                    or normalized(normalize_digits(a)) in src_digits
                    for a in alternatives)
                assert found, (
                    f"{c.case_id}: key fact {fact!r} not found in source text")

    def test_forbidden_facts_not_in_source(self):
        """A forbidden fact present in the SOURCE would flag correct answers."""
        for c in GOLD_CASES:
            src = normalized(c.input_text)
            for fact in c.forbidden_facts:
                assert normalized(fact) not in src, (
                    f"{c.case_id}: forbidden fact {fact!r} appears in source "
                    "— substring check would flag correct answers")

    def test_mock_echo_passes_all_cases(self):
        """The echo mock preserves every fact → checker must agree."""
        mock = _MockLLM()
        for c in GOLD_CASES:
            answer = mock.generate(
                f"TEXT:\n{c.input_text}\n\nAnswer language: {c.expected_lang}.")
            res = check_case_facts(answer, c)
            assert res["passed"], (
                f"{c.case_id}: mock echo failed facts: "
                f"missing={res['missing_facts']} "
                f"forbidden={res['forbidden_found']}")


class TestNegationGuard:
    """Negation cases need co-presence logic, not bare substrings."""

    def test_negation_case_flags_affirmative_inversion(self):
        case = next(c for c in GOLD_CASES if c.case_id == "np_negation_001")
        # model dropped the negation → must be caught
        res = check_case_facts("योजनाअन्तर्गत कर्जा र अनुदान उपलब्ध छन्।", case)
        assert not res["passed"], "affirmative inversion must fail"
        assert any("negation dropped" in f for f in res["forbidden_found"])

    def test_negation_case_passes_correct_negation(self):
        case = next(c for c in GOLD_CASES if c.case_id == "np_negation_001")
        res = check_case_facts(
            "योजनाअन्तर्गत सहुलियत कर्जा मात्र मिल्छ, अनुदान पाइँदैन।", case)
        assert res["passed"], res


class TestScoringLogic:
    """Unit tests for the deterministic scorers."""

    def test_detect_script(self):
        assert detect_script("यो नेपाली हो।") == "devanagari"
        assert detect_script("This is English.") == "latin"
        assert detect_script("passport को fee") == "mixed"
    def test_check_level_simple(self):
        ok = check_level("छोटो वाक्य। अर्को छोटो वाक्य।", "very_simple")
        assert ok["level_plausible"] is True

    def test_check_level_long_sentences_flagged(self):
        long_sent = "शब्द " * 40 + "।"
        ok = check_level(long_sent, "very_simple")
        assert ok["level_plausible"] is False

    def test_normalized_folds_whitespace(self):
        assert normalized("a\n  b\t c") == "a b c"


class TestEvaluatorPipeline:
    """The evaluator pipeline runs end-to-end in mock mode."""

    def test_mock_run_returns_summary(self):
        res = run_evaluator()
        assert res["summary"]["model"] == "mock"
        assert res["summary"]["n"] == len(GOLD_CASES)

    def test_mock_run_perfect_scores(self):
        """Echo mock → perfect fact preservation, no hallucinations."""
        res = run_evaluator()
        assert res["summary"]["all_facts_rate"] == 1.0
        assert res["summary"]["no_forbidden_rate"] == 1.0
