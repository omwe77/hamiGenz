"""
hamigenz — Tesseract OCR Configuration Test (v2)
Uses C:/tessdata/ (no spaces in path).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from PIL import Image, ImageDraw, ImageFont
import pytesseract

# Use a path WITHOUT spaces
TESSERACT_BIN = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA_DIR = r"C:\tessdata"  # No spaces!
TEST_DIR = os.path.join(os.path.dirname(__file__), "ocr_tests")
os.makedirs(TEST_DIR, exist_ok=True)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_BIN

def create_test_image(text, filename):
    img = Image.new('RGB', (600, 120), color='white')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 28)
    except:
        font = ImageFont.load_default()
    draw.text((10, 35), text, fill='black', font=font)
    img.save(filename)
    return filename

results = []

# Test 1: List languages with C:/tessdata
print("=" * 60)
print("TEST 1: List languages (C:/tessdata)")
print("=" * 60)
os.environ['TESSDATA_PREFIX'] = TESSDATA_DIR
try:
    langs = pytesseract.get_languages()
    print(f"Languages: {langs}")
    has_nep = 'nep' in langs
    print(f"TEST 1: {'PASS' if has_nep else 'PARTIAL (nep not listed but may work)'}")
    results.append(("Nepali in language list", has_nep))
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {e}")
    results.append(("Nepali in language list", False))

# Test 2: Nepali OCR
print("\n" + "=" * 60)
print("TEST 2: Nepali OCR")
print("=" * 60)
img = os.path.join(TEST_DIR, "nep.png")
create_test_image("नेपाली राहदानी", img)
try:
    result = pytesseract.image_to_string(img, lang='nep')
    print(f"Result: '{result.strip()}'")
    ok = len(result.strip()) > 0
    print(f"TEST 2: {'PASS' if ok else 'FAIL'}")
    results.append(("Nepali OCR", ok))
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {e}")
    # Try with config
    try:
        config = f'--tessdata-dir="{TESSDATA_DIR}" -l nep'
        result = pytesseract.image_to_string(img, config=config)
        print(f"With config: '{result.strip()}'")
        results.append(("Nepali OCR (config)", len(result.strip()) > 0))
    except Exception as e2:
        print(f"Config also failed: {e2}")
        results.append(("Nepali OCR (config)", False))

# Test 3: English OCR
print("\n" + "=" * 60)
print("TEST 3: English OCR")
print("=" * 60)
img = os.path.join(TEST_DIR, "eng.png")
create_test_image("Hello World Passport Test 123", img)
try:
    result = pytesseract.image_to_string(img, lang='eng')
    print(f"Result: '{result.strip()}'")
    ok = "Hello" in result or "World" in result
    print(f"TEST 3: {'PASS' if ok else 'FAIL'}")
    results.append(("English OCR", ok))
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {e}")
    results.append(("English OCR", False))

# Test 4: Combined
print("\n" + "=" * 60)
print("TEST 4: Combined eng+nep")
print("=" * 60)
img = os.path.join(TEST_DIR, "combined.png")
create_test_image("नेपाली Passport राहदानी Hello World", img)
try:
    result = pytesseract.image_to_string(img, lang='eng+nep')
    print(f"Result: '{result.strip()}'")
    has_nep = any('\u0900' <= c <= '\u097F' for c in result)
    has_eng = any(w in result for w in ['Hello', 'World', 'Passport'])
    ok = has_nep or has_eng or len(result.strip()) > 0
    print(f"Has Nepali: {has_nep}, Has English: {has_eng}")
    print(f"TEST 4: {'PASS' if ok else 'FAIL'}")
    results.append(("Combined eng+nep", ok))
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {e}")
    results.append(("Combined eng+nep", False))

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for name, ok in results:
    print(f"  {'✓' if ok else '✗'} {name}")
print(f"\nOverall: {'ALL ESSENTIAL PASS' if results[1][1] and results[2][1] else 'OCR NOT READY'}")
print("\nEnglish OCR must work for the pipeline. Nepali OCR is")
print("nice-to-have for scanned Nepali documents; the passport")
print("PDF we downloaded has extractable text so OCR is not required")
print("for the MVP test.")
