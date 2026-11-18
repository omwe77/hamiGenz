"""
hamigenz — Extended OCR engines: EasyOCR + TrOCR for Devanagari/handwriting

Extends the existing Tesseract-based OCR with optional deep-learning engines.

Tesseract is the primary engine and is always used first (fast, no GPU needed).
EasyOCR and TrOCR are optional secondaries; both fail gracefully when unavailable.

Usage:
    from ocr_engines import best_ocr_text, ocr_with_all_engines, diagnose_tesseract

    # Single best result
    text = best_ocr_text(img, prefer='nepali')

    # All-engine comparison (debugging / evaluation)
    results = ocr_with_all_engines(img)
    # → {'tesseract': '...', 'easyocr': '...', 'trocr': '...', 'best': '...'}

    # Print actionable diagnostic for missing language data
    diagnose_tesseract()
"""

from __future__ import annotations

import os
from typing import Optional

from PIL import Image

# ── Tesseract config (defer to document_processor's already-resolved paths) ───
#
# document_processor resolves TESSERACT_BIN and TESSDATA_PREFIX from env vars
# and known platform paths at import time.  We import it here so ocr_engines
# always uses the same binary and tessdata regardless of import order.
# ponytail: circular-import safe — document_processor does not import ocr_engines.

import pytesseract

try:
    from document_processor import (
        TESSERACT_BIN as _TESS_BIN,
        PROJECT_TESSDATA as _TESSDATA,
        get_available_languages as _get_tesseract_langs,
    )
    # Ensure pytesseract uses the same binary and tessdata as document_processor
    pytesseract.pytesseract.tesseract_cmd = str(_TESS_BIN)
    if _TESSDATA.exists():
        os.environ.setdefault("TESSDATA_PREFIX", str(_TESSDATA))
except ImportError:
    # Standalone / test usage: resolve independently
    import shutil
    from pathlib import Path

    _tess_bin_env = os.environ.get("TESSERACT_BIN", "")
    if _tess_bin_env:
        pytesseract.pytesseract.tesseract_cmd = _tess_bin_env
    elif Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe").exists():
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    else:
        found = shutil.which("tesseract")
        if found:
            pytesseract.pytesseract.tesseract_cmd = found

    def _get_tesseract_langs() -> list[str]:  # type: ignore[misc]
        try:
            return pytesseract.get_languages()
        except Exception:
            return []


# ── EasyOCR (optional — installed but not required for core pipeline) ─────────

try:
    import easyocr as _easyocr_mod
    _EASYOCR_AVAILABLE = True
except ImportError:
    _EASYOCR_AVAILABLE = False
    _easyocr_mod = None  # type: ignore

_easyocr_reader: Optional[object] = None
_easyocr_reader_langs: Optional[tuple[str, ...]] = None


def _get_easyocr_reader(langs: tuple[str, ...] = ("en", "ne")) -> Optional[object]:
    """Return a shared EasyOCR reader, initialised lazily."""
    global _easyocr_reader, _easyocr_reader_langs
    if _easyocr_reader is not None and _easyocr_reader_langs == langs:
        return _easyocr_reader
    if not _EASYOCR_AVAILABLE:
        return None
    try:
        _easyocr_reader = _easyocr_mod.Reader(list(langs), gpu=False, verbose=False)
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


# ── TrOCR via transformers (optional, lazy, offline-safe) ────────────────────
#
# TrOCR model loading is deferred to first use and requires the model to be
# already cached locally.  We never trigger a network download during a normal
# OCR request: if HF_HUB_OFFLINE=1 or the model is absent the load fails
# gracefully and falls back to Tesseract/EasyOCR.

try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    _TROCR_AVAILABLE = True
except ImportError:
    _TROCR_AVAILABLE = False
    TrOCRProcessor = None  # type: ignore
    VisionEncoderDecoderModel = None  # type: ignore

_trocr_processor: Optional[object] = None
_trocr_model: Optional[object] = None
_trocr_model_name: Optional[str] = None


def _get_trocr_model(model_name: str = "syubraj/TrOCR_Nepali"):
    """Lazily load a TrOCR model + processor from local cache only."""
    global _trocr_processor, _trocr_model, _trocr_model_name
    if _trocr_model is not None and _trocr_model_name == model_name:
        return _trocr_processor, _trocr_model
    if not _TROCR_AVAILABLE:
        return None, None
    try:
        print(f"[ocr_engines] Loading TrOCR model: {model_name}")
        # local_files_only=True prevents silent network downloads at request time.
        # ponytail: upgrade path — set local_files_only=False only in a
        # dedicated offline pre-download step (e.g. docker build).
        processor = TrOCRProcessor.from_pretrained(model_name, local_files_only=True)
        model = VisionEncoderDecoderModel.from_pretrained(model_name, local_files_only=True)
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
        pixel_values = processor(img, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values)
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return text.strip()
    except Exception as exc:
        print(f"[ocr_engines] TrOCR failed: {exc}")
        return ""


# ── Devanagari character counting ─────────────────────────────────────────────

_NEPALI_RANGE = (0x0900, 0x097F)


def _nepali_char_count(text: str) -> int:
    """Count Devanagari characters in text."""
    return sum(1 for c in text if _NEPALI_RANGE[0] <= ord(c) <= _NEPALI_RANGE[1])


# ── Diagnostics ───────────────────────────────────────────────────────────────

def diagnose_tesseract() -> dict[str, object]:
    """Return a dict describing Tesseract configuration and language availability.

    Prints actionable messages for any missing components.  Call this during
    startup or from health-check endpoints to surface misconfiguration early.
    """
    import shutil
    from pathlib import Path

    tess_cmd = pytesseract.pytesseract.tesseract_cmd
    tess_found = Path(tess_cmd).exists() if tess_cmd != "tesseract" else bool(shutil.which("tesseract"))
    tessdata_prefix = os.environ.get("TESSDATA_PREFIX", "")
    available_langs = _get_tesseract_langs()

    has_eng = "eng" in available_langs
    has_nep = "nep" in available_langs

    if not tess_found:
        print(
            f"[ocr_engines] WARN: Tesseract binary not found at '{tess_cmd}'.\n"
            "  Windows: install from https://github.com/UB-Mannheim/tesseract/wiki\n"
            "  Linux:   sudo apt-get install tesseract-ocr\n"
            "  Set TESSERACT_BIN env var to override the binary path."
        )
    if not has_nep:
        print(
            "[ocr_engines] WARN: Nepali traineddata ('nep') not available.\n"
            f"  TESSDATA_PREFIX={tessdata_prefix!r}\n"
            "  To install on Linux: sudo apt-get install tesseract-ocr-nep\n"
            "  To install on Windows: download nep.traineddata from\n"
            "    https://github.com/tesseract-ocr/tessdata/blob/main/nep.traineddata\n"
            "  and place it in your tessdata directory, or set TESSDATA_PREFIX."
        )
    if not has_eng:
        print(
            "[ocr_engines] WARN: English traineddata ('eng') not available.\n"
            f"  TESSDATA_PREFIX={tessdata_prefix!r}\n"
            "  To install on Linux: sudo apt-get install tesseract-ocr-eng\n"
            "  To install on Windows: download eng.traineddata from\n"
            "    https://github.com/tesseract-ocr/tessdata/blob/main/eng.traineddata"
        )

    return {
        "tesseract_cmd": tess_cmd,
        "tesseract_found": tess_found,
        "tessdata_prefix": tessdata_prefix,
        "available_languages": available_langs,
        "has_eng": has_eng,
        "has_nep": has_nep,
        "easyocr_available": _EASYOCR_AVAILABLE,
        "trocr_available": _TROCR_AVAILABLE,
    }


# ── Public API ─────────────────────────────────────────────────────────────────

def best_ocr_text(
    img: Image.Image,
    prefer: str = "nepali",
    tesseract_bin: Optional[str] = None,
) -> str:
    """Return the best OCR text for an image, trying multiple engines.

    Strategy:
      1. Run Tesseract (primary, fast, no GPU).
      2. If result has little Devanagari and prefer is 'nepali'/'handwriting',
         also run EasyOCR and keep whichever produced more Devanagari chars.
      3. TrOCR is only tried for prefer='handwriting' or if both others failed.

    Args:
        img: PIL Image to OCR.
        prefer: 'nepali' | 'handwriting' | 'english'
        tesseract_bin: optional override for Tesseract binary path.
    """
    if tesseract_bin:
        pytesseract.pytesseract.tesseract_cmd = tesseract_bin

    tess_languages = _get_tesseract_langs()
    tesseract_lang = _best_tesseract_lang(tess_languages, prefer)
    tesseract_text = ""
    if tesseract_lang:
        try:
            tesseract_text = pytesseract.image_to_string(img, lang=tesseract_lang, config="--psm 6")
        except Exception as exc:
            print(f"[ocr_engines] Tesseract failed: {exc}")

    best_text = tesseract_text
    best_nepali = _nepali_char_count(tesseract_text)

    # EasyOCR secondary pass for Devanagari content
    if prefer in ("nepali", "handwriting"):
        easyocr_text = _easyocr_ocr(img)
        easy_nepali = _nepali_char_count(easyocr_text)
        if easy_nepali > best_nepali:
            best_text = easyocr_text
            best_nepali = easy_nepali

    # TrOCR handwriting specialist (slower, only on request)
    if prefer == "handwriting":
        trocr_text = _trocr_ocr(img)
        if _nepali_char_count(trocr_text) > best_nepali and trocr_text:
            best_text = trocr_text

    # Last resort: EasyOCR English-only
    if not best_text.strip():
        fallback = _easyocr_ocr(img, langs=("en",))
        if fallback.strip():
            best_text = fallback

    return best_text


def ocr_with_all_engines(
    img: Image.Image,
    tesseract_bin: Optional[str] = None,
) -> dict[str, str]:
    """Run all available OCR engines on an image, return per-engine results.

    Useful for debugging OCR quality and comparing engines.
    """
    if tesseract_bin:
        pytesseract.pytesseract.tesseract_cmd = tesseract_bin

    results: dict[str, str] = {}

    tess_langs = _get_tesseract_langs()
    if tess_langs:
        try:
            for lang in (["nep", "eng+nep", "eng"] if "nep" in tess_langs else ["eng"]):
                if not all(l in tess_langs for l in lang.split("+")):
                    continue
                try:
                    results["tesseract"] = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
                    break
                except Exception:
                    continue
        except Exception as exc:
            print(f"[ocr_engines] Tesseract failed: {exc}")
            results["tesseract"] = ""

    results["easyocr"] = _easyocr_ocr(img)
    results["trocr"] = _trocr_ocr(img)

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


# ── Tesseract language selection helpers ──────────────────────────────────────

def _best_tesseract_lang(available: list[str], prefer: str) -> str:
    """Pick the best Tesseract language string for the given preference."""
    if not available:
        return ""
    has_nep = "nep" in available
    has_eng = "eng" in available
    if prefer == "english":
        return "eng" if has_eng else available[0]
    if prefer in ("nepali", "handwriting"):
        if has_nep:
            return "nep"
        if has_eng:
            return "eng"
    # default: nep if available, else eng+nep if both, else eng
    if has_nep:
        return "nep"
    if has_eng:
        return "eng"
    return available[0]
