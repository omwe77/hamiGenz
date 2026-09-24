---
type: OCRRule
title: Nepal Document OCR Post-Processing Rules
description: Rules for cleaning and correcting OCR output from Nepal official documents scanned with Tesseract.
tags: [ocr, post-processing, nepali, tesseract, correction, cleanup]
status: stable
verified:
  - {by: "hamiGenZ OKF curator", at: "2025-09-24T00:00:00Z"}
owner: "hamiGenZ document processing pipeline"
---

# Nepal Document OCR Post-Processing Rules

## Overview

After Tesseract OCR extracts text from Nepal documents (passports, citizenship certificates, ID cards, forms), apply these post-processing rules to clean up common OCR errors before the text enters the understanding pipeline.

## Rule 1: Normalize Devanagari digits

Tesseract sometimes outputs Devanagari digits (०१२३४५६७८९) for numeric fields even when the source has Latin digits (0123456789), or vice versa. Normalize to a consistent format based on context:

- **Dates (मिति / Date of Birth / Issue Date):** Convert to Latin digits `DD/MM/YYYY` for machine readability. Keep the original Devanagari in the text for display.
- **Citizenship/Passport numbers:** Keep as-is (could be alphanumeric). Do not normalize letters.
- **Fees/amounts with currency markers (रु, Rs.):** Normalize digits to Latin for extraction; keep currency marker.

Implementation note: use `str.translate()` with a Devanagari-to-Latin digit mapping when extracting structured fields.

## Rule 2: Fix broken spaces in Devanagari

Tesseract can insert spaces where none exist in Devanagari text, especially with complex conjuncts. Common issue: words get split mid-word.

Detection heuristic:
- If a Devanagari word fragment is very short (< 3 characters) and followed by another Devanagari fragment, try joining them.
- Check against a Nepali dictionary if available; if joined form is a valid word, merge.

Example: `"कागज अर"` → `"कागजार"` (if context supports it).

## Rule 3: Correct common OCR confusions

These Devanagari characters are commonly confused by OCR:

| Original | Common OCR error | Correction |
|---|---|---|
| `भ` (bha) | `भ` confused with `म` (ma) or `ध` (dha) | Check context — if word makes sense with correction, apply |
| `घ` (gha) | `घ` confused with `ध` (dha) or `ङ` | Contextual correction |
| `झ` (jha) | `झ` confused with `ध` | Contextual |
| `ढ` (dha) | `ढ` confused with `घ` or `ध` | Contextual |
| `ष` (sha) | `ष` confused with `श` (sha) or `स` (sa) | Contextual — ष and श look similar |
| `क्ष` (khya) | `क्ष` split into `क्` + `ष` or similar | Rejoin if split |
| `ह्र` / `क्ष्` / `त्र` | Common conjuncts broken | Rejoin |

Implementation: build a context-aware correction table — corrections applied only when the result is a known word or the original is an extremely rare character sequence.

## Rule 4: Normalize line breaks

OCR often inserts line breaks at page boundaries, column breaks, or between unrelated text blocks. Clean up:

- Merge lines that are clearly part of the same sentence (no terminal punctuation at line end, next line starts with lowercase or continuation).
- Preserve intentional paragraph breaks (blank lines, section headers).
- Remove excessive blank lines (more than 2 consecutive newlines → reduce to 1).

## Rule 5: Fix header/footer bleed

Pages often have repeating headers and footers (page numbers, document title, "नेपाल राहदानी" on every passport page, etc.). These appear in OCR output on every page.

- Identify repeating text blocks across pages.
- Remove or de-duplicate header/footer text from body content.
- Keep page numbers but tag them as metadata, not body text.

## Rule 6: Handle mixed-script pages

Nepal documents often mix Devanagari and English/Latin text on the same page (e.g., passport data page has both scripts side by side).

- Do NOT run Devanagari OCR correction on Latin text segments.
- Preserve the script boundary — keep English and Nepali as separate text blocks when possible.
- When extracting structured fields (name, DOB, passport number), check both scripts for the same field — the value may appear in either.

## Rule 7: MRZ (Machine Readable Zone) handling

Passport data pages have an MRZ at the bottom — standardized 2- or 3-line machine-readable text. This is NOT natural-language content.

- If the MRZ is present (detected by pattern: 2 lines of ~44 characters of mostly uppercase Latin + digits), separate it from the body text.
- The MRZ can be parsed deterministically (TD3 format) — do not feed it to the LLM as "document content." Use it for structured field extraction (passport number, DOB, nationality, expiry) and cross-check against the visually extracted fields.

## Rule 8: Confidence-based filtering

If OCR confidence data is available (Tesseract can output per-character confidence via `tsv` output):

- Flag low-confidence regions (average confidence < 60%) for manual review or LLM-assisted correction.
- High-confidence regions (> 85%) can be used as-is.
- Use confidence to weight the LLM's trust in different parts of the document.

## Rule 9: Image pre-processing to improve OCR

Before sending an image to Tesseract, apply:

- **Grayscale conversion** — reduces color noise.
- **Binarization/thresholding** — converts to black/white; helps with low-contrast scans.
- **Deskewing** — corrects slight rotation; Tesseract handles some skew but severe skew (> 5°) degrades results.
- **Denoising** — removes salt-and-pepper noise from poor scans.
- **Resolution check** — target 300 DPI for OCR; upscale if lower, downscale if much higher (reduces processing time without losing quality).

## Rule 10: Language model selection

For Nepal documents:

- Use the Nepali traineddata model (`nep`) for Devanagari-heavy pages — it outperforms `eng+nep` for Devanagari text (the English model interferes and produces garbage in Devanagari).
- Use `eng+nep` only when the page has significant English content alongside Nepali.
- Use `eng` for purely English pages.
- Run a script-detection heuristic first: if the page has > 30% Devanagari characters, prefer `nep` or `eng+nep`.

## Validation checklist after post-processing

Before sending cleaned text to the LLM understanding layer:

- [ ] No garbled characters (random symbols, box characters).
- [ ] Names are coherent and readable.
- [ ] Dates are in a recognized format (DD/MM/YYYY or localized equivalent).
- [ ] Field labels are distinguishable from field values (headers vs body).
- [ ] No obvious OCR hallucination (made-up text not present in the image).
- [ ] The document structure is preserved (page 1 = data page, etc.).
