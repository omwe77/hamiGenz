"""Unit tests for action_extractor.py — normalization & URL safety rules."""
import os
import sys
import pytest

_BACKEND = os.path.dirname(os.path.dirname(__file__))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from action_extractor import (
    normalize_digits,
    normalize_currency,
    is_safe_official_url,
    sanitize_url,
    extract_fee_hints,
)


class TestNormalizeDigits:
    def test_ascii_digits_unaltered(self):
        assert normalize_digits("12345") == "12345"

    def test_nepali_digits_converted(self):
        # ०१२३४५६७८९ -> 0123456789
        nepali_str = "\u0966\u0967\u0968\u0969\u096a\u096b\u096c\u096d\u096e\u096f"
        assert normalize_digits(nepali_str) == "0123456789"

    def test_mixed_text(self):
        nepali_fee = "\u0967\u0966\u0966\u0966 rupees"
        assert normalize_digits(nepali_fee) == "1000 rupees"


class TestNormalizeCurrency:
    def test_rs_canonicalized(self):
        assert normalize_currency("Rs.500") == "Rs. 500"
        assert normalize_currency("rs 1500") == "Rs. 1500"

    def test_npr_canonicalized(self):
        assert normalize_currency("NPR 2000") == "NPR 2000"
        assert normalize_currency("npr 500") == "NPR 500"


class TestSafeOfficialUrl:
    def test_gov_np_allowed(self):
        assert is_safe_official_url("https://nepalpassport.gov.np") is True
        assert is_safe_official_url("https://moha.gov.np/services") is True

    def test_edu_and_org_np_allowed(self):
        assert is_safe_official_url("https://tu.edu.np") is True
        assert is_safe_official_url("https://redcross.org.np") is True

    def test_commercial_and_phishing_rejected(self):
        assert is_safe_official_url("https://fake-gov-np.com") is False
        assert is_safe_official_url("http://phishing.site/nepal") is False
        assert is_safe_official_url("javascript:alert(1)") is False
        assert is_safe_official_url("data:text/html,bad") is False


class TestSanitizeUrl:
    def test_trims_and_preserves_valid(self):
        assert sanitize_url(" https://nepalpassport.gov.np ") == "https://nepalpassport.gov.np"

    def test_strips_invalid_scheme(self):
        assert sanitize_url("ftp://gov.np") is None
        assert sanitize_url("not a url") is None