"""
hamigenz — Tesseract OCR Configuration Diagnostic Script (Manual Utility)

Run directly for manual environment verification:
    python tests/test_ocr.py

This script is protected with an if __name__ == "__main__": guard to ensure
it is not executed during automatic pytest collection. Deterministic automated
unit tests reside in tests/test_ocr_engines.py.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

# Add backend to sys.path
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from PIL import Image, ImageDraw, ImageFont
import pytesseract

try:
    from document_processor import TESSERACT_BIN as _DEFAULT_BIN, PROJECT_TESSDATA as _DEFAULT_TESSDATA
    TESSERACT_BIN = str(_DEFAULT_BIN)
    TESSDATA_DIR = str(_DEFAULT_TESSDATA)
except ImportError:
    TESSERACT_BIN = os.environ.get(
        "TESSERACT_BIN",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe").exists()
        else shutil.which("tesseract") or "tesseract",
    )
    TESSDATA_DIR = os.environ.get("TESSDATA_PREFIX", str(Path(__file__).resolve().parent.parent / "data" / "tessdata"))

TEST_DIR = Path(__file__).resolve().parent / "ocr_tests"


def create_test_image(text: str, filename: Path | str) -> str:
    img = Image.new("RGB", (600, 120), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
    draw.text((10, 35), text, fill="black", font=font)
    img.save(str(filename))
    return str(filename)


def run_diagnostics() -> None:
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_BIN
    if Path(TESSDATA_DIR).exists():
        os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR

    results = []

    print("=" * 60)
    print("TEST 1: List languages")
    print("=" * 60)
    print(f"Binary:   {TESSERACT_BIN}")
    print(f"Tessdata: {TESSDATA_DIR}")
    try:
        langs = pytesseract.get_languages()
        print(f"Languages: {langs}")
        has_nep = "nep" in langs
        print(f"TEST 1: {'PASS' if has_nep else 'PARTIAL (nep not listed but may work)'}")
        results.append(("Nepali in language list", has_nep))
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        results.append(("Nepali in language list", False))

    print("\n" + "=" * 60)
    print("TEST 2: Nepali OCR")
    print("=" * 60)
    img = TEST_DIR / "nep.png"
    create_test_image("नेपाली राहदानी", img)
    try:
        result = pytesseract.image_to_string(str(img), lang="nep")
        print(f"Result: '{result.strip()}'")
        ok = len(result.strip()) > 0
        print(f"TEST 2: {'PASS' if ok else 'FAIL'}")
        results.append(("Nepali OCR", ok))
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        try:
            config = f'--tessdata-dir="{TESSDATA_DIR}" -l nep'
            result = pytesseract.image_to_string(str(img), config=config)
            print(f"With config: '{result.strip()}'")
            results.append(("Nepali OCR (config)", len(result.strip()) > 0))
        except Exception as e2:
            print(f"Config also failed: {e2}")
            results.append(("Nepali OCR (config)", False))

    print("\n" + "=" * 60)
    print("TEST 3: English OCR")
    print("=" * 60)
    img = TEST_DIR / "eng.png"
    create_test_image("Hello World Passport Test 123", img)
    try:
        result = pytesseract.image_to_string(str(img), lang="eng")
        print(f"Result: '{result.strip()}'")
        ok = "Hello" in result or "World" in result
        print(f"TEST 3: {'PASS' if ok else 'FAIL'}")
        results.append(("English OCR", ok))
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        results.append(("English OCR", False))

    print("\n" + "=" * 60)
    print("TEST 4: Combined eng+nep")
    print("=" * 60)
    img = TEST_DIR / "combined.png"
    create_test_image("नेपाली Passport राहदानी Hello World", img)
    try:
        result = pytesseract.image_to_string(str(img), lang="eng+nep")
        print(f"Result: '{result.strip()}'")
        has_nep = any("\u0900" <= c <= "\u097F" for c in result)
        has_eng = any(w in result for w in ["Hello", "World", "Passport"])
        ok = has_nep or has_eng or len(result.strip()) > 0
        print(f"Has Nepali: {has_nep}, Has English: {has_eng}")
        print(f"TEST 4: {'PASS' if ok else 'FAIL'}")
        results.append(("Combined eng+nep", ok))
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        results.append(("Combined eng+nep", False))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, ok in results:
        print(f"  {'✓' if ok else '✗'} {name}")
    print(f"\nOverall: {'ALL ESSENTIAL PASS' if len(results) >= 3 and results[1][1] and results[2][1] else 'OCR NOT READY'}")


if __name__ == "__main__":
    run_diagnostics()
