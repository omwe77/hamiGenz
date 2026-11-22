"""
tests/test_ocr_engines.py — Deterministic unit tests for backend/ocr_engines.py

All tests are self-contained and do not require a live Tesseract binary,
network access, or GPU.  Real-OCR integration tests are skipped automatically
when Tesseract or the Nepali traineddata is unavailable.
"""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

# ---------------------------------------------------------------------------
# Make sure backend/ is importable when running from repo root via pytest
# ---------------------------------------------------------------------------
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

try:
    from document_processor import (
        TESSERACT_BIN as _DEFAULT_BIN,
        PROJECT_TESSDATA as _DEFAULT_TESSDATA,
    )
    import pytesseract
    if Path(str(_DEFAULT_BIN)).exists():
        pytesseract.pytesseract.tesseract_cmd = str(_DEFAULT_BIN)
    if _DEFAULT_TESSDATA.exists():
        os.environ.setdefault("TESSDATA_PREFIX", str(_DEFAULT_TESSDATA))
except ImportError:
    pass


def _blank_image(width: int = 200, height: int = 50) -> Image.Image:
    return Image.new("RGB", (width, height), color="white")


def _tesseract_available() -> bool:
    import shutil
    import pytesseract
    cmd = pytesseract.pytesseract.tesseract_cmd
    return (
        Path(cmd).exists()
        if cmd and cmd != "tesseract"
        else bool(shutil.which("tesseract"))
    )


def _lang_available(lang: str) -> bool:
    if not _tesseract_available():
        return False
    try:
        import pytesseract
        return lang in pytesseract.get_languages()
    except Exception:
        return False


SKIP_NO_TESS = pytest.mark.skipif(
    not _tesseract_available(), reason="Tesseract binary not available"
)
SKIP_NO_NEP = pytest.mark.skipif(
    not _lang_available("nep"), reason="Nepali traineddata ('nep') not installed"
)
SKIP_NO_ENG = pytest.mark.skipif(
    not _lang_available("eng"), reason="English traineddata ('eng') not installed"
)


# ---------------------------------------------------------------------------
# UNIT: _nepali_char_count
# ---------------------------------------------------------------------------

class TestNepaliCharCount:
    def test_counts_devanagari(self):
        from ocr_engines import _nepali_char_count
        assert _nepali_char_count("नमस्ते") == 6

    def test_ignores_latin(self):
        from ocr_engines import _nepali_char_count
        assert _nepali_char_count("Hello World") == 0

    def test_mixed(self):
        from ocr_engines import _nepali_char_count
        assert _nepali_char_count("नमस्ते World") == 6

    def test_empty(self):
        from ocr_engines import _nepali_char_count
        assert _nepali_char_count("") == 0


# ---------------------------------------------------------------------------
# UNIT: _best_tesseract_lang
# ---------------------------------------------------------------------------

class TestBestTesseractLang:
    def _call(self, available, prefer):
        from ocr_engines import _best_tesseract_lang
        return _best_tesseract_lang(available, prefer)

    def test_nepali_prefer_gives_nep_when_available(self):
        assert self._call(["eng", "nep", "osd"], "nepali") == "nep"

    def test_english_prefer_gives_eng(self):
        assert self._call(["eng", "nep"], "english") == "eng"

    def test_nepali_prefer_falls_back_to_eng_when_nep_absent(self):
        assert self._call(["eng", "osd"], "nepali") == "eng"

    def test_handwriting_prefer_gives_nep_when_available(self):
        assert self._call(["eng", "nep"], "handwriting") == "nep"

    def test_empty_available_returns_empty(self):
        assert self._call([], "nepali") == ""

    def test_nep_only_available(self):
        result = self._call(["nep"], "english")
        # eng not available, falls through to available[0]
        assert result == "nep"


# ---------------------------------------------------------------------------
# UNIT: diagnose_tesseract
# ---------------------------------------------------------------------------

class TestDiagnoseTesseract:
    def test_returns_expected_keys(self):
        from ocr_engines import diagnose_tesseract
        result = diagnose_tesseract()
        expected_keys = {
            "tesseract_cmd", "tesseract_found", "tessdata_prefix",
            "available_languages", "has_eng", "has_nep",
            "easyocr_available", "trocr_available",
        }
        assert expected_keys.issubset(result.keys())

    def test_has_eng_matches_available_languages(self):
        from ocr_engines import diagnose_tesseract
        result = diagnose_tesseract()
        assert result["has_eng"] == ("eng" in result["available_languages"])

    def test_has_nep_matches_available_languages(self):
        from ocr_engines import diagnose_tesseract
        result = diagnose_tesseract()
        assert result["has_nep"] == ("nep" in result["available_languages"])

    def test_easyocr_available_bool(self):
        from ocr_engines import diagnose_tesseract, _EASYOCR_AVAILABLE
        result = diagnose_tesseract()
        assert result["easyocr_available"] == _EASYOCR_AVAILABLE

    def test_trocr_available_bool(self):
        from ocr_engines import diagnose_tesseract, _TROCR_AVAILABLE
        result = diagnose_tesseract()
        assert result["trocr_available"] == _TROCR_AVAILABLE

    def test_missing_binary_flagged(self, tmp_path):
        """When tesseract_cmd points to a nonexistent path, tesseract_found=False."""
        import pytesseract
        import ocr_engines
        orig = pytesseract.pytesseract.tesseract_cmd
        try:
            pytesseract.pytesseract.tesseract_cmd = str(tmp_path / "no_such_binary")
            result = ocr_engines.diagnose_tesseract()
            assert result["tesseract_found"] is False
        finally:
            pytesseract.pytesseract.tesseract_cmd = orig


# ---------------------------------------------------------------------------
# UNIT: EasyOCR graceful degradation when unavailable
# ---------------------------------------------------------------------------

class TestEasyOCRDegradation:
    def test_returns_empty_when_unavailable(self):
        import ocr_engines
        orig = ocr_engines._EASYOCR_AVAILABLE
        orig_reader = ocr_engines._easyocr_reader
        try:
            ocr_engines._EASYOCR_AVAILABLE = False
            ocr_engines._easyocr_reader = None
            result = ocr_engines._easyocr_ocr(_blank_image())
            assert result == ""
        finally:
            ocr_engines._EASYOCR_AVAILABLE = orig
            ocr_engines._easyocr_reader = orig_reader

    def test_reader_init_exception_returns_empty(self):
        import ocr_engines
        orig_available = ocr_engines._EASYOCR_AVAILABLE
        orig_mod = ocr_engines._easyocr_mod
        orig_reader = ocr_engines._easyocr_reader
        orig_langs = ocr_engines._easyocr_reader_langs
        try:
            mock_mod = MagicMock()
            mock_mod.Reader.side_effect = RuntimeError("no model")
            ocr_engines._EASYOCR_AVAILABLE = True
            ocr_engines._easyocr_mod = mock_mod
            ocr_engines._easyocr_reader = None
            ocr_engines._easyocr_reader_langs = None
            result = ocr_engines._get_easyocr_reader(("en",))
            assert result is None
        finally:
            ocr_engines._EASYOCR_AVAILABLE = orig_available
            ocr_engines._easyocr_mod = orig_mod
            ocr_engines._easyocr_reader = orig_reader
            ocr_engines._easyocr_reader_langs = orig_langs


# ---------------------------------------------------------------------------
# UNIT: TrOCR graceful degradation
# ---------------------------------------------------------------------------

class TestTrOCRDegradation:
    def test_returns_empty_when_unavailable(self):
        import ocr_engines
        orig = ocr_engines._TROCR_AVAILABLE
        orig_proc = ocr_engines._trocr_processor
        orig_model = ocr_engines._trocr_model
        try:
            ocr_engines._TROCR_AVAILABLE = False
            ocr_engines._trocr_processor = None
            ocr_engines._trocr_model = None
            result = ocr_engines._trocr_ocr(_blank_image())
            assert result == ""
        finally:
            ocr_engines._TROCR_AVAILABLE = orig
            ocr_engines._trocr_processor = orig_proc
            ocr_engines._trocr_model = orig_model

    def test_load_failure_returns_none_pair(self, tmp_path):
        """Model load failure (e.g. no cached model) returns (None, None)."""
        import ocr_engines
        orig_available = ocr_engines._TROCR_AVAILABLE
        orig_proc = ocr_engines._trocr_processor
        orig_model = ocr_engines._trocr_model
        orig_name = ocr_engines._trocr_model_name
        try:
            ocr_engines._TROCR_AVAILABLE = True
            ocr_engines._trocr_processor = None
            ocr_engines._trocr_model = None
            ocr_engines._trocr_model_name = None
            # Patch from_pretrained to simulate missing cached model
            with patch("ocr_engines.TrOCRProcessor") as mock_proc:
                mock_proc.from_pretrained.side_effect = OSError("model not cached")
                p, m = ocr_engines._get_trocr_model("test/model")
            assert p is None
            assert m is None
        finally:
            ocr_engines._TROCR_AVAILABLE = orig_available
            ocr_engines._trocr_processor = orig_proc
            ocr_engines._trocr_model = orig_model
            ocr_engines._trocr_model_name = orig_name


# ---------------------------------------------------------------------------
# UNIT: best_ocr_text — mocked Tesseract path
# ---------------------------------------------------------------------------

class TestBestOCRTextMocked:
    """Tests best_ocr_text() logic without touching the real Tesseract binary."""

    def _mock_tess(self, return_value: str = ""):
        return patch("ocr_engines.pytesseract.image_to_string", return_value=return_value)

    def _mock_langs(self, langs: list[str]):
        return patch("ocr_engines._get_tesseract_langs", return_value=langs)

    def _mock_easyocr(self, return_value: str = ""):
        return patch("ocr_engines._easyocr_ocr", return_value=return_value)

    def test_tesseract_result_returned_when_good(self):
        import ocr_engines
        with self._mock_langs(["eng", "nep"]), \
             self._mock_tess("नमस्ते"), \
             self._mock_easyocr(""):
            result = ocr_engines.best_ocr_text(_blank_image(), prefer="nepali")
        assert "नमस्ते" in result

    def test_easyocr_wins_when_more_devanagari(self):
        import ocr_engines
        with self._mock_langs(["eng", "nep"]), \
             self._mock_tess("hello"), \
             self._mock_easyocr("नमस्ते देश"):
            result = ocr_engines.best_ocr_text(_blank_image(), prefer="nepali")
        assert "नमस्ते" in result

    def test_english_prefer_uses_eng_lang(self):
        import ocr_engines
        calls = []

        def capture_lang(img, lang=None, config=None):
            calls.append(lang)
            return "Hello"

        with self._mock_langs(["eng", "nep"]), \
             patch("ocr_engines.pytesseract.image_to_string", side_effect=capture_lang):
            ocr_engines.best_ocr_text(_blank_image(), prefer="english")
        assert calls and calls[0] == "eng"

    def test_fallback_easyocr_when_tesseract_empty(self):
        """When Tesseract returns empty, the last-resort EasyOCR fallback is used."""
        import ocr_engines
        # prefer="english" skips the mid-path EasyOCR pass, so only the
        # last-resort branch fires. Mock a single call that returns "fallback text".
        with self._mock_langs(["eng"]), \
             self._mock_tess(""), \
             patch("ocr_engines._easyocr_ocr", return_value="fallback text"):
            result = ocr_engines.best_ocr_text(_blank_image(), prefer="english")
        assert result == "fallback text"

    def test_missing_lang_data_handled_gracefully(self):
        """When no languages available, best_ocr_text returns empty string, not exception."""
        import ocr_engines
        with self._mock_langs([]), \
             self._mock_easyocr(""):
            result = ocr_engines.best_ocr_text(_blank_image(), prefer="nepali")
        assert isinstance(result, str)

    def test_tesseract_exception_handled_gracefully(self):
        import ocr_engines
        with self._mock_langs(["eng"]), \
             patch("ocr_engines.pytesseract.image_to_string", side_effect=Exception("tess crash")), \
             self._mock_easyocr(""):
            result = ocr_engines.best_ocr_text(_blank_image(), prefer="english")
        assert isinstance(result, str)

    def test_easyocr_skipped_when_devanagari_threshold_met(self):
        """When Tesseract returns >= 10 Devanagari chars, EasyOCR secondary pass is skipped."""
        import ocr_engines
        easyocr_mock = MagicMock()
        with self._mock_langs(["eng", "nep"]), \
             self._mock_tess("नेपाल सरकारको कार्यालय"), \
             patch("ocr_engines._easyocr_ocr", easyocr_mock):
            result = ocr_engines.best_ocr_text(_blank_image(), prefer="nepali")
        assert "नेपाल" in result
        assert easyocr_mock.call_count == 0, "EasyOCR should be skipped when threshold >= 10 is met"

    def test_easyocr_runs_when_devanagari_insufficient(self):
        """When Tesseract returns < 10 Devanagari chars, EasyOCR secondary pass runs."""
        import ocr_engines
        easyocr_mock = MagicMock(return_value="नेपाल सरकारको आधिकारिक सूचना")
        with self._mock_langs(["eng", "nep"]), \
             self._mock_tess("नेपा"), \
             patch("ocr_engines._easyocr_ocr", easyocr_mock):
            result = ocr_engines.best_ocr_text(_blank_image(), prefer="nepali")
        assert easyocr_mock.call_count >= 1, "EasyOCR should run when Tesseract Devanagari is < 10 chars"
        assert "सूचना" in result

    def test_handwriting_preference_invokes_easyocr_and_trocr(self):
        """prefer='handwriting' invokes both EasyOCR and TrOCR regardless of Tesseract char count."""
        import ocr_engines
        easyocr_mock = MagicMock(return_value="हस्तलिखित फारम")
        trocr_mock = MagicMock(return_value="हस्तलिखित फारम ट्रओसीआर आधिकारिक दस्तावेज")
        with self._mock_langs(["eng", "nep"]), \
             self._mock_tess("हस्त"), \
             patch("ocr_engines._easyocr_ocr", easyocr_mock), \
             patch("ocr_engines._trocr_ocr", trocr_mock):
            result = ocr_engines.best_ocr_text(_blank_image(), prefer="handwriting")
        assert easyocr_mock.call_count >= 1
        assert trocr_mock.call_count >= 1
        assert "ट्रओसीआर" in result

    def test_trocr_fallback_when_primary_engines_empty(self):
        """When Tesseract and EasyOCR return empty text, TrOCR fallback is invoked."""
        import ocr_engines
        trocr_mock = MagicMock(return_value="TrOCR fallback result")
        with self._mock_langs(["eng", "nep"]), \
             self._mock_tess(""), \
             patch("ocr_engines._easyocr_ocr", return_value=""), \
             patch("ocr_engines._trocr_ocr", trocr_mock):
            result = ocr_engines.best_ocr_text(_blank_image(), prefer="nepali")
        assert trocr_mock.call_count >= 1
        assert result == "TrOCR fallback result"


# ---------------------------------------------------------------------------
# INTEGRATION: Real Tesseract (skipped when not configured)
# ---------------------------------------------------------------------------

class TestTesseractIntegration:
    @SKIP_NO_TESS
    @SKIP_NO_ENG
    def test_english_ocr_produces_text(self):
        """Real Tesseract can OCR a rendered English image."""
        from PIL import ImageDraw, ImageFont
        import ocr_engines

        img = Image.new("RGB", (400, 60), "white")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 24)
        except Exception:
            font = ImageFont.load_default()
        draw.text((10, 15), "Hello World", fill="black", font=font)

        import pytesseract
        text = pytesseract.image_to_string(img, lang="eng", config="--psm 6")
        assert "Hello" in text or "World" in text, f"Unexpected: {text!r}"

    @SKIP_NO_TESS
    @SKIP_NO_NEP
    def test_nepali_ocr_produces_devanagari(self):
        """Real Tesseract with nep traineddata produces Devanagari output from fixture.

        Asserts expected transcription for tests/ocr_tests/nep.png using NFC Unicode
        normalization and computes Character Error Rate (CER) via Levenshtein distance.
        """
        import unicodedata
        from ocr_engines import _nepali_char_count

        fixture = Path(__file__).parent / "ocr_tests" / "nep.png"
        assert fixture.exists(), "Nepali OCR fixture image missing (tests/ocr_tests/nep.png)"

        import pytesseract
        img = Image.open(str(fixture))
        raw_text = pytesseract.image_to_string(img, lang="nep", config="--psm 6")
        normalized = unicodedata.normalize("NFC", raw_text).strip()

        # Known expected transcription rendered in fixture
        expected = "नेपाल सरकार"
        assert normalized == expected, (
            f"Expected transcription {expected!r}, got {normalized!r}"
        )

        # Calculate exact Character Error Rate (CER) via Levenshtein edit distance
        ref = expected
        hyp = normalized
        d = [[0] * (len(hyp) + 1) for _ in range(len(ref) + 1)]
        for i in range(len(ref) + 1):
            d[i][0] = i
        for j in range(len(hyp) + 1):
            d[0][j] = j
        for i in range(1, len(ref) + 1):
            for j in range(1, len(hyp) + 1):
                cost = 0 if ref[i - 1] == hyp[j - 1] else 1
                d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
        cer = d[len(ref)][len(hyp)] / max(len(ref), 1)
        assert cer == 0.0, f"Expected CER 0.0, got {cer}"
        assert _nepali_char_count(normalized) >= 5

    @SKIP_NO_TESS
    def test_diagnose_tesseract_tess_found_true(self):
        from ocr_engines import diagnose_tesseract
        info = diagnose_tesseract()
        assert info["tesseract_found"] is True

    @SKIP_NO_TESS
    def test_ocr_with_all_engines_returns_dict(self):
        from ocr_engines import ocr_with_all_engines
        result = ocr_with_all_engines(_blank_image())
        assert isinstance(result, dict)
        assert "tesseract" in result or "easyocr" in result
        assert "best" in result


# ---------------------------------------------------------------------------
# INTEGRATION: Offline / missing traineddata
# ---------------------------------------------------------------------------

class TestOfflineBehavior:
    def test_easyocr_download_disabled_flag(self):
        """EasyOCR Reader must always be initialised with download_enabled=False."""
        import ocr_engines
        orig_available = ocr_engines._EASYOCR_AVAILABLE
        orig_mod = ocr_engines._easyocr_mod
        orig_reader = ocr_engines._easyocr_reader
        orig_langs = ocr_engines._easyocr_reader_langs
        try:
            calls: list[dict] = []

            def capturing_reader(*args, **kwargs):
                calls.append(kwargs)
                raise RuntimeError("simulated: no models cached")

            mock_mod = MagicMock()
            mock_mod.Reader = capturing_reader
            ocr_engines._EASYOCR_AVAILABLE = True
            ocr_engines._easyocr_mod = mock_mod
            ocr_engines._easyocr_reader = None
            ocr_engines._easyocr_reader_langs = None

            ocr_engines._get_easyocr_reader(("en",))
        finally:
            ocr_engines._EASYOCR_AVAILABLE = orig_available
            ocr_engines._easyocr_mod = orig_mod
            ocr_engines._easyocr_reader = orig_reader
            ocr_engines._easyocr_reader_langs = orig_langs
        assert calls, "EasyOCR Reader was never called"
        assert calls[0].get("download_enabled") is False, (
            "EasyOCR Reader must be called with download_enabled=False to prevent "
            "silent network downloads when model files are missing"
        )

    def test_easyocr_missing_models_fallback(self):
        """When EasyOCR models are absent, _get_easyocr_reader returns None gracefully."""
        import ocr_engines
        orig_available = ocr_engines._EASYOCR_AVAILABLE
        orig_mod = ocr_engines._easyocr_mod
        orig_reader = ocr_engines._easyocr_reader
        orig_langs = ocr_engines._easyocr_reader_langs
        try:
            mock_mod = MagicMock()
            mock_mod.Reader.side_effect = FileNotFoundError("model not found")
            ocr_engines._EASYOCR_AVAILABLE = True
            ocr_engines._easyocr_mod = mock_mod
            ocr_engines._easyocr_reader = None
            ocr_engines._easyocr_reader_langs = None
            result = ocr_engines._get_easyocr_reader(("en",))
        finally:
            ocr_engines._EASYOCR_AVAILABLE = orig_available
            ocr_engines._easyocr_mod = orig_mod
            ocr_engines._easyocr_reader = orig_reader
            ocr_engines._easyocr_reader_langs = orig_langs
        assert result is None, "Should return None when model files are absent"

    def test_missing_nep_handled_gracefully(self):
        """With nep excluded from available langs, best_ocr_text should not crash."""
        import ocr_engines
        with patch("ocr_engines._get_tesseract_langs", return_value=["eng"]), \
             patch("ocr_engines.pytesseract.image_to_string", return_value="fallback"), \
             patch("ocr_engines._easyocr_ocr", return_value=""):
            result = ocr_engines.best_ocr_text(_blank_image(), prefer="nepali")
        assert isinstance(result, str)

    def test_no_tesseract_binary_handled_gracefully(self):
        """With no tesseract binary, best_ocr_text falls back to EasyOCR."""
        import ocr_engines
        with patch("ocr_engines._get_tesseract_langs", return_value=[]), \
             patch("ocr_engines._easyocr_ocr", return_value="easyocr fallback"):
            result = ocr_engines.best_ocr_text(_blank_image(), prefer="nepali")
        assert result == "easyocr fallback"

    def test_trocr_local_files_only_prevents_network_download(self):
        """_get_trocr_model must pass local_files_only=True to prevent network calls."""
        import ocr_engines
        orig_available = ocr_engines._TROCR_AVAILABLE
        orig_proc = ocr_engines._trocr_processor
        orig_model = ocr_engines._trocr_model
        orig_name = ocr_engines._trocr_model_name
        try:
            ocr_engines._TROCR_AVAILABLE = True
            ocr_engines._trocr_processor = None
            ocr_engines._trocr_model = None
            ocr_engines._trocr_model_name = None
            calls = []

            def capturing_from_pretrained(name, **kwargs):
                calls.append(kwargs)
                raise OSError("not cached")  # simulate missing local model

            with patch("ocr_engines.TrOCRProcessor") as mock_proc:
                mock_proc.from_pretrained.side_effect = capturing_from_pretrained
                ocr_engines._get_trocr_model("test/model")

            assert calls, "from_pretrained was not called"
            assert calls[0].get("local_files_only") is True, (
                "TrOCR must pass local_files_only=True to prevent silent network downloads"
            )
        finally:
            ocr_engines._TROCR_AVAILABLE = orig_available
            ocr_engines._trocr_processor = orig_proc
            ocr_engines._trocr_model = orig_model
            ocr_engines._trocr_model_name = orig_name
