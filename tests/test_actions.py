"""
Offline tests for the action extractor (no LLM, no live server).

Run: .venv/Scripts/python.exe -m pytest tests/test_actions.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from action_extractor import (
    ActionExtractor,
    extract_fee_hints,
    extract_deadline_hints,
    extract_link_hints,
    normalize_date,
    normalize_fee_amount,
    normalize_digits,
    sanitize_url,
    is_safe_official_url,
)


class TestNormalization:
    def test_nepali_digits(self):
        assert normalize_digits("रु ५००") == "रु 500"
        assert normalize_digits("मिति २०८१/०३/१५") == "मिति 2081/03/15"

    def test_day_first_dates(self):
        assert normalize_date("15/03/2081") == "2081-03-15"
        assert normalize_date("3-1-2025") == "2025-01-03"

    def test_ambiguous_swaps_to_day_first(self):
        # 03/15/2025 cannot be day-first (month 15 invalid) → swapped
        assert normalize_date("03/15/2025") == "2025-03-15"

    def test_currency_canonicalization(self):
        assert "Rs." in normalize_fee_amount("रु ५००")
        assert "Rs. 500" == normalize_fee_amount("Rs. 500")
        assert "NPR" in normalize_fee_amount("npr 1,000")


class TestFeeHints:
    def test_rs_amount(self):
        hints = extract_fee_hints("The fee is Rs. 500 for a 34-page passport.")
        assert len(hints) == 1
        assert "500" in hints[0]["amount"]
        assert "Rs." in hints[0]["amount"]

    def test_devanagari_fee(self):
        hints = extract_fee_hints("प्रयोग शुल्क रु १५०० तिर्नुपर्छ।")
        assert len(hints) == 1
        assert "1500" in hints[0]["amount"]

    def test_npr_amount(self):
        hints = extract_fee_hints("Pay NPR 2,500 at the counter.")
        assert len(hints) == 1
        assert "2,500" in hints[0]["amount"] or "2500" in hints[0]["amount"]

    def test_no_fees(self):
        assert extract_fee_hints("Bring your citizenship card.") == []


class TestDeadlineHints:
    def test_date_with_deadline_language(self):
        hints = extract_deadline_hints("Submit before 15/08/2081. Last date for forms.")
        assert any("2081-08-15" == h["date"] for h in hints)

    def test_plain_date_still_captured(self):
        hints = extract_deadline_hints("Notice dated 01/01/2081.")
        assert len(hints) >= 1

    def test_iso_date(self):
        hints = extract_deadline_hints("Deadline is 2081-05-12.")
        assert any(h["date"] == "2081-05-12" for h in hints)


class TestLinkHints:
    def test_official_url_kept(self):
        urls = extract_link_hints("Visit www.nepalpassport.gov.np for details.")
        assert len(urls) == 1
        assert urls[0].startswith("https://")

    def test_unofficial_url_dropped(self):
        assert extract_link_hints("Visit www.example-random-site.com now.") == []

    def test_garbled_scheme_fixed(self):
        urls = extract_link_hints("See https:///www.nepalpolice.gov.np/notice")
        assert urls == [] or all(u.startswith("https://") for u in urls)


class TestUrlSafety:
    def test_gov_np_allowed(self):
        assert is_safe_official_url("https://www.nepalpassport.gov.np/x")

    def test_non_http_rejected(self):
        assert not is_safe_official_url("ftp://www.nepalpassport.gov.np")
        assert not is_safe_official_url("javascript:alert(1)")

    def test_lookalike_rejected(self):
        assert not is_safe_official_url("https://gov.np.evil.example.com")

    def test_sanitize_adds_scheme(self):
        assert sanitize_url("www.nrb.org.np") == "https://www.nrb.org.np"


class TestExtractorGuards:
    """Test the normalization/guard logic without an LLM."""

    def setup_method(self):
        self.ext = ActionExtractor(llm=None)

    def test_str_list_filters_garbage(self):
        assert self.ext._str_list(["a", "", None, "b"]) == ["a", "b"]
        assert self.ext._str_list("not-a-list") == []
        assert self.ext._str_list([123]) == ["123"]

    def test_obj_list_normalizes(self):
        out = self.ext._obj_list(
            [{"amount": "Rs. 500", "description": "fee"}, "flat string"],
            ("amount", "description"),
        )
        assert out[0]["amount"] == "Rs. 500"
        assert out[1] == {"amount": "flat string", "description": ""}

    def test_links_sanitized_and_capped(self):
        raw = [{"url": "www.nepalpassport.gov.np", "description": "passport"},
               {"url": "https://evil.example.com", "description": "bad"}]
        out = self.ext._links(raw)
        assert len(out) == 1
        assert "nepalpassport.gov.np" in out[0]["url"]

    def test_hallucination_guard_flags_unknown_fees(self):
        actions = {"fees": [{"amount": "Rs. 99999", "description": "mystery"}],
                   "deadlines": []}
        hints = {"fees": [{"amount": "Rs. 500", "context": ""}],
                 "deadlines": []}
        guarded = self.ext._guard_against_hallucination(actions, hints)
        assert guarded["fees"][0]["unverified"] is True

    def test_hallucination_guard_flags_unknown_dates(self):
        actions = {"fees": [], "deadlines": [{"date": "2099-01-01", "description": "x"}]}
        hints = {"fees": [], "deadlines": [{"date": "2081-03-15"}]}
        guarded = self.ext._guard_against_hallucination(actions, hints)
        assert guarded["deadlines"][0]["unverified"] is True

    def test_hallucination_guard_passes_known(self):
        actions = {"fees": [{"amount": "Rs. 500", "description": "fee"}], "deadlines": []}
        hints = {"fees": [{"amount": "Rs. 500", "context": ""}], "deadlines": []}
        guarded = self.ext._guard_against_hallucination(actions, hints)
        assert "unverified" not in guarded["fees"][0]

    def test_wrap_adds_meta(self):
        out = self.ext._wrap({"requirements": []}, "hints_only", "note text")
        assert out["meta"] == {"status": "hints_only", "note": "note text"}
