"""
Offline tests for form understanding (PR-010) — no LLM, no live server.

Uses realistic Nepali + English form text samples.

Run: .venv/Scripts/python.exe -m pytest tests/test_forms.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from form_understanding import (
    detect_form,
    extract_fields,
    FormUnderstandingService,
    SAMPLE_HEADER,
    SAMPLE_FOOTER,
    _strip_realistic_ids,
    _clean_label,
)

# ─── Realistic samples ────────────────────────────────────────────

NEPALI_APPLICATION_FORM = """नेपाल नागरिकता प्रमाणपत्र आवेदन फारम

नाम थर: ______________________
ठेगाना: ______________________
जन्म मिति: ______________________
नागरिकता नम्बर: ______________________
बाबुको नाम: ______________________
आमाको नाम: ______________________
फोन नम्बर: ______________________
हस्ताक्षर: ______________________

कागजात तपसील: नागरिकता, पासपोर्ट साइज फोटो
"""

ENGLISH_APPLICATION_FORM = """PASSPORT APPLICATION FORM

Full Name: ______________________
Date of Birth: ______________________
Place of Birth: ______________________
Father's Name: ______________________
Mother's Name: ______________________
Permanent Address: ______________________
Phone Number: ______________________
Email Address: ______________________
Occupation: ______________________
Signature: ______________________
Date: ______________________
"""

PLAIN_NOTICE = """The Department of Passports announces that passport fees have been
revised from 1st Shrawan 2081. Ordinary 34-page: Rs. 5000. Ordinary 66-page:
Rs. 10000. Applicants must book appointments online at www.nepalpassport.gov.np
and bring their citizenship certificate and a printed appointment confirmation.
"""

CHECKBOX_FORM = """[ ] Full name
[ ] Date of birth
[X] Marital status
[ ] Occupation
Applicant's declaration: I hereby declare the above is true.
"""


class TestFormDetection:
    def test_nepali_form_detected(self):
        d = detect_form(NEPALI_APPLICATION_FORM)
        assert d["is_form"] is True
        assert d["field_count"] >= 6
        assert d["confidence"] > 0.4

    def test_english_form_detected(self):
        d = detect_form(ENGLISH_APPLICATION_FORM)
        assert d["is_form"] is True
        assert d["field_count"] >= 8

    def test_plain_notice_not_a_form(self):
        d = detect_form(PLAIN_NOTICE)
        assert d["is_form"] is False

    def test_empty_text(self):
        d = detect_form("")
        assert d["is_form"] is False
        assert d["field_count"] == 0

    def test_checkbox_form_detected(self):
        d = detect_form(CHECKBOX_FORM)
        assert d["field_count"] >= 3


class TestFieldExtraction:
    def test_nepali_fields_found(self):
        fields = extract_fields(NEPALI_APPLICATION_FORM)
        labels = {f["label"] for f in fields}
        assert "नाम थर" in labels
        assert "ठेगाना" in labels
        assert "जन्म मिति" in labels
        assert "हस्ताक्षर" in labels

    def test_english_fields_found(self):
        fields = extract_fields(ENGLISH_APPLICATION_FORM)
        labels = {f["label"].lower() for f in fields}
        assert "full name" in labels
        assert "date of birth" in labels
        assert "permanent address" in labels

    def test_fields_carry_evidence(self):
        fields = extract_fields(NEPALI_APPLICATION_FORM)
        for f in fields:
            assert "evidence" in f
            assert f["label"] in f["evidence"] or f["evidence"]

    def test_page_markers_respected(self):
        text = "[PAGE 1]\nName: ____\nAddress: ____\n[PAGE 2]\nSignature: ____\nDate: ____"
        fields = extract_fields(text)
        pages = {f["page"] for f in fields}
        assert pages == {1, 2}

    def test_notice_yields_few_fields(self):
        fields = extract_fields(PLAIN_NOTICE)
        assert len(fields) < 4

    def test_label_cap(self):
        fields = extract_fields(ENGLISH_APPLICATION_FORM)
        assert all(len(f["label"].split()) <= 8 for f in fields)


class TestLabelCleaning:
    def test_rejects_instruction_lines(self):
        assert _clean_label("Please fill in block letters") is None
        assert _clean_label("Note that fees are non-refundable") is None

    def test_rejects_long_sentences(self):
        assert _clean_label("This is a very long sentence that keeps going on and on and should be rejected") is None

    def test_accepts_normal_label(self):
        assert _clean_label("Full Name") == "Full Name"


class TestSafetyGuards:
    def test_realistic_ids_stripped(self):
        assert _strip_realistic_ids("ID: 1234567890") == "ID: " + "X" * 8
        assert _strip_realistic_ids("short 12345 ok") == "short 12345 ok"

    def test_sample_markers_present_in_explanations(self):
        svc = FormUnderstandingService(llm=None)
        out = svc._fallback("नाम थर", "नाम थर: ____ (form context)", "note")
        assert SAMPLE_HEADER in out["sample_markers"]
        assert SAMPLE_FOOTER in out["sample_markers"]
        assert out["meta"]["status"] == "hints_only"

    def test_fallback_quotes_field_wording(self):
        svc = FormUnderstandingService(llm=None)
        out = svc._fallback("Full Name", "Full Name: ____", "note")
        assert "Full Name" in out["source_quote"]

    def test_wrap_adds_meta(self):
        svc = FormUnderstandingService(llm=None)
        out = svc._wrap({"meaning": "x"}, "llm", "note!")
        assert out["meta"] == {"status": "llm", "note": "note!"}
