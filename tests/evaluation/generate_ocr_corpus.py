"""
hamiGenZ — Deterministic OCR Evaluation Corpus Generator.
Generates 5 canonical test images with ground-truth text for OCR benchmark evaluation:
1. 01_digital_clean: High-contrast, clean Devanagari text.
2. 02_scanned_noise: Simulated document texture with slight grain/contrast.
3. 03_lowres_blur: Reduced resolution with slight Gaussian blur.
4. 04_rotated_skew: Document page with a 2-degree skew angle.
5. 05_mixed_bilingual: Mixed Nepali Devanagari, English alphanumeric, dates, fees.
"""
from __future__ import annotations

import os
import random
import unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CORPUS_DIR = Path(__file__).resolve().parent / "ocr_corpus"
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

# Select best available font
FONT_PATHS = [
    r"C:\Windows\Fonts\Nirmala.ttc",
    r"C:\Windows\Fonts\mangal.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
]

def get_font(size: int = 28) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

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
