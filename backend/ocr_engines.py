"""
hamigenz — Extended OCR engines: EasyOCR + TrOCR for Devanagari/handwriting

Extends the existing Tesseract-based OCR with:

1. EasyOCR (installed, CPU) — a deep-learning OCR engine with native
   Devanagari support.  Used as a secondary engine: we run Tesseract first
   (fast, already configured), then EasyOCR on pages where Tesseract
   produced little/nothing, and keep the result with more Devanagari chars.

   EasyOCR uses the CRAFT text detector + CRNN recognizer and handles
   multi-line, multi-orientation text well.  The 'ne' (Nepali) model
   provides Devanagari recognition.

2. TrOCR (via transformers, already installed) — a Vision Transformer
   encoder + text Transformer decoder for scene-text / handwriting OCR.
   We load syubraj/TrOCR_Nepali (Devanagari fine-tuned) lazily on first
   use and fall back to EasyOCR/Tesseract if it cannot be loaded.

   TrOCR is especially useful for handwritten field values on Nepali
   citizenship cards and similar documents.

Usage:
    from ocr_engines import best_ocr_text, ocr_with_all_engines

    # Single best result (tries Tesseract, EasyOCR, TrOCR; picks best)
    text = best_ocr_text(img, prefer='nepali')

    # All-engine comparison (for debugging / evaluation)
    results = ocr_with_all_engines(img)
    # → {'tesseract': '...', 'easyocr': '...', 'trocr': '...', 'best': '...'}
"""

from __future__ import annotations

import re
from typing import Optional

from PIL import Image

# ── EasyOCR (always available, installed as dependency) ──────────────────────

try:
    import easyocr
    _EASYOCR_AVAILABLE = True
except ImportError:
    _EASYOCR_AVAILABLE = False
    easyocr = None  # type: ignore

# EasyOCR reader: lazily initialised on first use (model download + load).
_easyocr_reader: Optional["easyocr.Reader"] = None
_easyocr_reader_langs: Optional[tuple[str, ...]] = None


def _get_easyocr_reader(langs: tuple[str, ...] = ("en", "ne")) -> Optional["easyocr.Reader"]:
    """Return a shared EasyOCR reader, initialised lazily."""
    global _easyocr_reader, _easyocr_reader_langs
    if _easyocr_reader is not None and _easyocr_reader_langs == langs:
        return _easyocr_reader
    if not _EASYOCR_AVAILABLE:
        return None
    try:
        _easyocr_reader = easyocr.Reader(list(langs), gpu=False, verbose=False)
        _easyocr_reader_langs = langs
        return _easyocr_reader
    except Exception as exc:
        print(f"[ocr_engines] EasyOCR initialisation failed: {exc}")
        return None


def _easyocr_ocr(img: Image.Image, langs: tuple[str, ...] = ("en", "ne")) -> str:
    """Run EasyOCR on a PIL image, return concatenated text."""
    reader = _get_easyocr_reader(langs)
    if reader is None:
        return ""
    try:
        results = reader.readtext(
            img,
            paragraph=True,
            min_size=20,
            width_ths=0.5,
            height_ths=0.5,
            text_threshold=0.7,
            low_text=0.4,
        )
        # results: list of (bbox, text, confidence)
        texts = [r[1] for r in results if r[1].strip()]
        return "\n".join(texts)
    except Exception as exc:
        print(f"[ocr_engines] EasyOCR failed: {exc}")
        return ""


# ── TrOCR via transformers (lazy, optional) ──────────────────────────────────

try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    _TROCR_AVAILABLE = True
except ImportError:
    _TROCR_AVAILABLE = False
    TrOCRProcessor = None  # type: ignore
    VisionEncoderDecoderModel = None  # type: ignore

# TrOCR model: lazily loaded on first use.
_trocr_processor: Optional[TrOCRProcessor] = None
_trocr_model: Optional[VisionEncoderDecoderModel] = None
_trocr_model_name: Optional[str] = None


def _get_trocr_model(model_name: str = "syubraj/TrOCR_Nepali"):
    """Lazily load a TrOCR model + processor."""
    global _trocr_processor, _trocr_model, _trocr_model_name
    if _trocr_model is not None and _trocr_model_name == model_name:
        return _trocr_processor, _trocr_model
    if not _TROCR_AVAILABLE:
        return None, None
    try:
        print(f"[ocr_engines] Loading TrOCR model: {model_name}")
        processor = TrOCRProcessor.from_pretrained(model_name)
        model = VisionEncoderDecoderModel.from_pretrained(model_name)
        _trocr_processor = processor
        _trocr_model = model
        _trocr_model_name = model_name
        print(f"[ocr_engines] TrOCR loaded OK: {model_name}")
        return processor, model
    except Exception as exc:
        print(f"[ocr_engines] TrOCR load failed ({model_name}): {exc}")
        return None, None


def _trocr_ocr(img: Image.Image) -> str:
    """Run TrOCR on a PIL image, return recognised text."""
    processor, model = _get_trocr_model()
    if processor is None or model is None:
        return ""
    try:
        # TrOCR expects 224x224 or similar — processor handles resizing.
        pixel_values = processor(img, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values)
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return text.strip()
    except Exception as exc:
        print(f"[ocr_engines] TrOCR failed: {exc}")
        return ""


# ── Devanagari character counting (shared) ────────────────────────────────────

_NEPALI_RANGE = (0x0900, 0x097F)


def _nepali_char_count(text: str) -> int:
    """Count Devanagari characters in text."""
    return sum(1 for c in text if _NEPALI_RANGE[0] <= ord(c) <= _NEPALI_RANGE[1])


# ── Public API ─────────────────────────────────────────────────────────────────

def best_ocr_text(
    img: Image.Image,
    prefer: str = "nepali",
    tesseract_bin: Optional[str] = None,
) -> str:
    """Return the best OCR text for an image, trying multiple engines.

    Strategy:
      1. Run Tesseract (already configured, fast).
      2. If Tesseract produced little Devanagari text, run EasyOCR.
      3. Pick whichever produced more Devanagari characters.
      4. TrOCR is available as a third engine but is slower — only used if
         explicitly requested via prefer='handwriting' or if both Tesseract
         and EasyOCR failed.

    Args:
        img: PIL Image to OCR.
        prefer: 'nepali' (maximise Devanagari chars), 'handwriting' (try TrOCR
                first for handwritten content), 'english' (maximise Latin text).
        tesseract_bin: optional path to tesseract binary (passed to pytesseract).
    """
    import pytesseract

    # ── 1. Tesseract (primary, fast) ────────────────────────────────────────
    tess_languages = _get_tesseract_langs()
    tesseract_lang = _best_tesseract_lang(tess_languages, prefer)
    tesseract_text = ""
    if tesseract_lang:
        try:
            if tesseract_bin:
                pytesseract.pytesseract.tesseract_cmd = tesseract_bin
            tesseract_text = pytesseract.image_to_string(img, lang=tesseract_lang, config="--psm 6")
        except Exception as exc:
            print(f"[ocr_engines] Tesseract failed: {exc}")

    best_text = tesseract_text
    best_nepali = _nepali_char_count(tesseract_text)
    best_source = "tesseract"

    # ── 2. EasyOCR (secondary, deeper Devanagari) ───────────────────────────
    if prefer in ("nepali", "handwriting"):
        easyocr_text = _easyocr_ocr(img)
        easy_nepali = _nepali_char_count(easyocr_text)
        if easy_nepali > best_nepali:
            best_text = easyocr_text
            best_nepali = easy_nepali
            best_source = "easyocr"

    # ── 3. TrOCR (handwriting specialist, slower) ────────────────────────────
    if prefer == "handwriting":
        trocr_text = _trocr_ocr(img)
        trocr_nepali = _nepali_char_count(trocr_text)
        if trocr_nepali > best_nepali and trocr_text:
            best_text = trocr_text
            best_nepali = trocr_nepali
            best_source = "trocr"

    # ── Fallback: if everything failed, try EasyOCR with English-only ────────
    if not best_text.strip():
        easyocr_text = _easyocr_ocr(img, langs=("en",))
        if easyocr_text.strip():
            best_text = easyocr_text
            best_source = "easyocr(en)"

    return best_text


def ocr_with_all_engines(
    img: Image.Image,
    tesseract_bin: Optional[str] = None,
) -> dict[str, str]:
    """Run all available OCR engines on an image, return per-engine results.

    Useful for debugging OCR quality and comparing Tesseract vs EasyOCR vs TrOCR.
    """
    import pytesseract

    results: dict[str, str] = {}

    # Tesseract
    tess_langs = _get_tesseract_langs()
    if tess_langs:
        try:
            if tesseract_bin:
                pytesseract.pytesseract.tesseract_cmd = tesseract_bin
            # Try Nepali first, then English
            for lang in (reversed(tess_langs) if "nep" in tess_langs else tess_langs):
                try:
                    results["tesseract"] = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
                    break
                except Exception:
                    continue
        except Exception as exc:
            print(f"[ocr_engines] Tesseract failed: {exc}")
            results["tesseract"] = ""

    # EasyOCR
    results["easyocr"] = _easyocr_ocr(img)

    # TrOCR
    results["trocr"] = _trocr_ocr(img)

    # Best (by Devanagari char count)
    best = ""
    best_nepali = 0
    best_source = ""
    for source, text in results.items():
        nepali = _nepali_char_count(text)
        if nepali > best_nepali:
            best = text
            best_nepali = nepali
            best_source = source
    results["best"] = best
    results["best_source"] = best_source
    return results


# ── Tesseract helpers (reuse existing logic) ──────────────────────────────────

_tess_languages_cache: Optional[list[str]] = None


def _get_tesseract_langs() -> list[str]:
    """Return available Tesseract languages (cached)."""
    global _tess_languages_cache
    if _tess_languages_cache is None:
        try:
            _tess_languages_cache = pytesseract.get_languages()
        except Exception:
            _tess_languages_cache = []
    return _tess_languages_cache


def _best_tesseract_lang(available: list[str], prefer: str) -> str:
    """Pick the best Tesseract language for the preference."""
    if prefer == "nepali" and "nep" in available:
        return "nep"
    if "eng" in available:
        return "eng" if prefer == "english" else "eng+nep" if "nep" in available else "eng"
    return available[0] if available else ""
