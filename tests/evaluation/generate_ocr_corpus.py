"""
hamiGenZ — Deterministic OCR Evaluation Corpus Generator.
Generates 5 canonical test images with ground-truth text for OCR benchmark evaluation:
1. 01_digital_clean: High-contrast, clean Devanagari text.
2. 02_scanned_noise: Simulated document texture with slight grain/contrast.
3. 03_lowres_blur: Reduced resolution with slight Gaussian blur.
4. 04_rotated_skew: Document page with a 2-degree skew angle.
5. 05_mixed_bilingual: Mixed Nepali Devanagari, English alphanumeric, dates, fees.

Cross-OS reproducibility note:
  Windows selects Nirmala.ttc while Linux selects NotoSansDevanagari-Regular.ttf
  (or kalimati.ttf / Lohit-Devanagari.ttf). Because these are distinct typefaces
  with different glyph metrics, re-running this generator across OSes will not
  produce bit-for-bit identical PNG bytes. The benchmark (eval_ocr.py) evaluates
  the committed PNGs under tests/evaluation/ocr_corpus/ for deterministic CI results.
"""
from __future__ import annotations

import os
import random
import struct
import unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CORPUS_DIR = Path(__file__).resolve().parent / "ocr_corpus"
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

# Select best available font with Devanagari script support
FONT_PATHS = [
    # Windows
    r"C:\Windows\Fonts\Nirmala.ttc",
    r"C:\Windows\Fonts\mangal.ttf",
    r"C:\Windows\Fonts\aparaj.ttf",
    # Linux (Debian / Ubuntu: fonts-deva, fonts-noto-core, fonts-lohit-deva)
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/truetype/deva/kalimati.ttf",
    "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
    # macOS
    "/System/Library/Fonts/Supplemental/DevanagariMT.ttc",
]
# Deliberately excluded: DejaVuSans.ttf (Latin only), FreeSerif.ttf (incomplete
# Devanagari), KohinoorBangla.ttc (Bengali script, not Devanagari).

_DEVA_PROBE = "नेपाल"  # Probe string for coverage verification
_DEVA_PROBE_CODEPOINTS = tuple(dict.fromkeys(ord(ch) for ch in _DEVA_PROBE))


def _cmap_lookup_format4(data: bytes, sub_off: int, cp: int) -> int:
    if cp > 0xFFFF:
        return 0
    seg_count_x2 = struct.unpack_from(">H", data, sub_off + 6)[0]
    seg_count = seg_count_x2 // 2
    end_off = sub_off + 14
    start_off = end_off + seg_count_x2 + 2
    delta_off = start_off + seg_count_x2
    range_off = delta_off + seg_count_x2
    for i in range(seg_count):
        end_code = struct.unpack_from(">H", data, end_off + 2 * i)[0]
        if cp > end_code:
            continue
        start_code = struct.unpack_from(">H", data, start_off + 2 * i)[0]
        if cp < start_code:
            return 0
        id_delta = struct.unpack_from(">h", data, delta_off + 2 * i)[0]
        id_range_off = struct.unpack_from(">H", data, range_off + 2 * i)[0]
        if id_range_off == 0:
            return (cp + id_delta) & 0xFFFF
        glyph_idx_off = range_off + 2 * i + id_range_off + 2 * (cp - start_code)
        gid = struct.unpack_from(">H", data, glyph_idx_off)[0]
        return 0 if gid == 0 else (gid + id_delta) & 0xFFFF
    return 0


def _cmap_lookup_format12(data: bytes, sub_off: int, cp: int) -> int:
    num_groups = struct.unpack_from(">I", data, sub_off + 12)[0]
    groups_off = sub_off + 16
    for i in range(num_groups):
        start_c, end_c, start_gid = struct.unpack_from(">III", data, groups_off + 12 * i)
        if start_c <= cp <= end_c:
            return start_gid + (cp - start_c)
        if cp < start_c:
            break
    return 0


def _font_covers_codepoints(font_path: str, codepoints: tuple[int, ...]) -> bool:
    """Verify via SFNT cmap table that every codepoint maps to a non-zero glyph."""
    try:
        data = Path(font_path).read_bytes()
    except OSError:
        return False
    if len(data) < 12:
        return False

    tag = data[:4]
    if tag == b"ttcf":
        num_fonts = struct.unpack_from(">I", data, 8)[0]
        if num_fonts < 1 or len(data) < 16:
            return False
        font_off = struct.unpack_from(">I", data, 12)[0]
    elif tag in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
        font_off = 0
    else:
        return False

    num_tables = struct.unpack_from(">H", data, font_off + 4)[0]
    cmap_off = None
    for i in range(num_tables):
        rec_off = font_off + 12 + 16 * i
        t_tag, _, t_off, _ = struct.unpack_from(">4sIII", data, rec_off)
        if t_tag == b"cmap":
            cmap_off = t_off
            break
    if cmap_off is None:
        return False

    num_subtables = struct.unpack_from(">H", data, cmap_off + 2)[0]
    for i in range(num_subtables):
        plat_id, enc_id, rel_off = struct.unpack_from(">HHI", data, cmap_off + 4 + 8 * i)
        # Prefer Unicode (platform 0) or Windows Unicode BMP/full (platform 3, enc 1/10)
        if not (plat_id == 0 or (plat_id == 3 and enc_id in (1, 10))):
            continue
        sub_off = cmap_off + rel_off
        fmt = struct.unpack_from(">H", data, sub_off)[0]
        if fmt == 4 and all(_cmap_lookup_format4(data, sub_off, cp) > 0 for cp in codepoints):
            return True
        if fmt == 12 and all(_cmap_lookup_format12(data, sub_off, cp) > 0 for cp in codepoints):
            return True
    return False


def get_font(size: int = 28) -> ImageFont.FreeTypeFont:
    """Return a TrueType font capable of rendering Devanagari glyphs.

    Verification:
      1. Inspect the font's SFNT cmap table to confirm all Devanagari probe
         codepoints map to non-zero glyph IDs (rejects Latin-only fonts whose
         .notdef tofu boxes would otherwise render non-blank pixels).
      2. Render the probe string with Pillow and confirm both a non-blank
         bitmap and non-.notdef glyph masks.

    Raises RuntimeError when no suitable font is found; never falls back to
    PIL's bitmap default font.
    """
    probe_w, probe_h = 200, 60
    blank = Image.new("RGB", (probe_w, probe_h), "white")
    blank_pixels = set(blank.getdata())

    for path in FONT_PATHS:
        if not os.path.exists(path):
            continue
        if not _font_covers_codepoints(path, _DEVA_PROBE_CODEPOINTS):
            continue
        try:
            font = ImageFont.truetype(path, size)
            # Rendering check: non-blank bitmap and not identical to .notdef mask
            notdef_mask = bytes(font.getmask("\uffff"))
            if any(
                not bytes(font.getmask(chr(cp))) or bytes(font.getmask(chr(cp))) == notdef_mask
                for cp in _DEVA_PROBE_CODEPOINTS
            ):
                continue
            probe_img = Image.new("RGB", (probe_w, probe_h), "white")
            ImageDraw.Draw(probe_img).text((5, 5), _DEVA_PROBE, fill=(0, 0, 0), font=font)
            if set(probe_img.getdata()) != blank_pixels:
                return font
        except Exception:
            continue
    raise RuntimeError(
        "No Devanagari-capable font found (must pass both SFNT cmap coverage and "
        "non-.notdef rendering checks). Install one of: Nirmala UI (Windows), "
        "fonts-noto-core or fonts-deva (Linux). "
        "Silent fallback to bitmap default font is forbidden."
    )

def render_document(lines: list[str], font_size: int = 28, pad: int = 40, width: int = 900) -> Image.Image:
    font = get_font(font_size)
    line_height = int(font_size * 1.6)
    height = pad * 2 + len(lines) * line_height
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    y = pad
    for line in lines:
        draw.text((pad, y), line, fill=(15, 23, 42), font=font)
        y += line_height
    return img

def main():
    random.seed(42)  # Deterministic seed

    # 1. Digital Clean (Nepali administrative notice)
    text_01 = [
        "नेपाल सरकार, गृह मन्त्रालय",
        "नागरिकता तथा राष्ट्रिय परिचयपत्र सम्बन्धी जरुरी सूचना",
        "नागरिकता प्रमाणपत्रको प्रतिलिपि प्राप्त गर्न वडा कार्यालयको सिफारिस अनिवार्य छ।",
        "निवेदन साथ सक्कल नागरिकता वा सोको प्रतिलिपि पेस गर्नुपर्नेछ।",
    ]
    gt_01 = unicodedata.normalize("NFC", "\n".join(text_01))
    img_01 = render_document(text_01, font_size=28)
    img_01.save(CORPUS_DIR / "01_digital_clean.png")
    (CORPUS_DIR / "01_digital_clean.gt.txt").write_text(gt_01, encoding="utf-8")
    # 2. Scanned Noise (Simulated document paper texture)
    text_02 = [
        "राहदानी विभाग, काठमाडौँ",
        "साधारण ३४ पृष्ठको ई-पासपोर्ट दस्तुर रु. ५,००० निर्धारण गरिएको छ।",
        "सेवाग्राहीले अनलाइन आवेदन फाराम भरी मिति र समय सुरक्षित गर्नुपर्नेछ।",
    ]
    gt_02 = unicodedata.normalize("NFC", "\n".join(text_02))
    img_02 = render_document(text_02, font_size=28)
    # Add subtle salt-and-pepper grain
    pixels = img_02.load()
    w, h = img_02.size
    for _ in range(int(w * h * 0.008)):
        rx = random.randint(0, w - 1)
        ry = random.randint(0, h - 1)
        gray = random.randint(180, 240)
        pixels[rx, ry] = (gray, gray, gray)
    img_02.save(CORPUS_DIR / "02_scanned_noise.png")
    (CORPUS_DIR / "02_scanned_noise.gt.txt").write_text(gt_02, encoding="utf-8")
    # 3. Low-res Blur (Simulated low-bandwidth or compression artifact)
    text_03 = [
        "सवारी चालक अनुमतिपत्र कार्यालय",
        "लिखित परीक्षा उत्तीर्ण भएपछि प्रयोगात्मक परीक्षा दिन पाइनेछ।",
        "नवीकरण म्याद नाघेको अवस्थामा नियमानुसार जरिवाना लाग्नेछ।",
    ]
    gt_03 = unicodedata.normalize("NFC", "\n".join(text_03))
    img_03 = render_document(text_03, font_size=28)
    # Downscale and upscale with slight Gaussian blur
    w3, h3 = img_03.size
    img_03_small = img_03.resize((w3 // 2, h3 // 2), Image.Resampling.BILINEAR)
    img_03 = img_03_small.resize((w3, h3), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(radius=0.6))
    img_03.save(CORPUS_DIR / "03_lowres_blur.png")
    (CORPUS_DIR / "03_lowres_blur.gt.txt").write_text(gt_03, encoding="utf-8")

    # 4. Rotated Skew (2 degrees slight scanner tilt)
    text_04 = [
        "राष्ट्रिय परिचयपत्र तथा पञ्जीकरण विभाग",
        "व्यक्तिगत घटना (जन्म, मृत्यु, विवाह) ३५ दिनभित्र दर्ता गराउनुहोला।",
        "तोकिएको समयभित्र दर्ता गराएमा कुनै पनि दस्तुर लाग्ने छैन।",
    ]
    gt_04 = unicodedata.normalize("NFC", "\n".join(text_04))
    img_04_raw = render_document(text_04, font_size=28)
    img_04 = img_04_raw.rotate(2.0, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(255, 255, 255))
    img_04.save(CORPUS_DIR / "04_rotated_skew.png")
    (CORPUS_DIR / "04_rotated_skew.gt.txt").write_text(gt_04, encoding="utf-8")

    # 5. Mixed Bilingual (Devanagari + English + numbers + B.S./A.D. dates)
    text_05 = [
        "Government of Nepal - Ministry of Foreign Affairs",
        "e-Passport Application Notice / विद्युतीय राहदानी सम्बन्धी सूचना",
        "Standard Fee: NPR 5,000 (34 pages) | Urgent Fee: NPR 12,000",
        "Effective Date: 2081-05-01 B.S. (17 August 2024)",
        "Official Portal: https://nepalpassport.gov.np",
    ]
    gt_05 = unicodedata.normalize("NFC", "\n".join(text_05))
    img_05 = render_document(text_05, font_size=26)
    img_05.save(CORPUS_DIR / "05_mixed_bilingual.png")
    (CORPUS_DIR / "05_mixed_bilingual.gt.txt").write_text(gt_05, encoding="utf-8")

    print(f"Successfully generated 5 evaluation corpus cases in {CORPUS_DIR}")

if __name__ == "__main__":
    main()
