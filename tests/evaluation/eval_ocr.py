"""
hamiGenZ — OCR Evaluation Benchmark Runner.

Evaluates OCR quality (CER and WER) on the canonical Devanagari/bilingual evaluation corpus.
Uses standard library Levenshtein distance to avoid external heavy dependencies.
"""
from __future__ import annotations

import os
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from PIL import Image

# Ensure backend is on sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import document_processor
import pytesseract

CORPUS_DIR = Path(__file__).resolve().parent / "ocr_corpus"


def levenshtein_distance(seq1: list | str, seq2: list | str) -> int:
    """Standard dynamic programming Levenshtein distance."""
    m, n = len(seq1), len(seq2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if seq1[i - 1] == seq2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]


def compute_cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate: edit_dist(chars) / len(ref_chars)."""
    ref_norm = unicodedata.normalize("NFC", reference.strip())
    hyp_norm = unicodedata.normalize("NFC", hypothesis.strip())
    if not ref_norm:
        return 0.0 if not hyp_norm else 1.0
    dist = levenshtein_distance(ref_norm, hyp_norm)
    return dist / len(ref_norm)


def compute_wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate: edit_dist(words) / len(ref_words)."""
    ref_words = unicodedata.normalize("NFC", reference).split()
    hyp_words = unicodedata.normalize("NFC", hypothesis).split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    dist = levenshtein_distance(ref_words, hyp_words)
    return dist / len(ref_words)


@dataclass
class CaseResult:
    case_id: str
    description: str
    ref_chars: int
    hyp_chars: int
    ref_words: int
    hyp_words: int
    cer: float
    wer: float
    extracted_text: str


SUPPORTED_ENGINES = ("tesseract", "easyocr", "trocr")


def run_ocr_eval(engine: str = "tesseract") -> dict:
    if engine not in SUPPORTED_ENGINES:
        raise ValueError(
            f"Unsupported OCR engine: '{engine}'. Supported engines: {list(SUPPORTED_ENGINES)}. "
            "Silent fallback to empty text is rejected."
        )

    if not CORPUS_DIR.exists():
        raise FileNotFoundError(f"Corpus dir not found: {CORPUS_DIR}. Run generate_ocr_corpus.py first.")

    image_files = sorted(CORPUS_DIR.glob("*.png"))
    if not image_files:
        raise ValueError(f"No test images (*.png) found in {CORPUS_DIR}")

    results = []

    # Ensure tesseract language settings
    avail_langs = document_processor.get_available_languages()
    lang_str = "nep" if "nep" in avail_langs else "eng"
    if "nep" in avail_langs and "eng" in avail_langs:
        lang_str = "nep+eng"

    for img_path in image_files:
        stem = img_path.stem
        gt_path = CORPUS_DIR / f"{stem}.gt.txt"
        if not gt_path.exists():
            raise ValueError(f"Malformed OCR corpus: missing ground truth file for {img_path.name}")
        gt_text = gt_path.read_text(encoding="utf-8").strip()
        if not gt_text:
            raise ValueError(f"Malformed OCR corpus: ground truth file {gt_path.name} is empty")

        with Image.open(img_path) as img:
            if engine == "tesseract":
                # For pure Nepali documents, use 'nep' if available, for mixed use 'nep+eng'
                case_lang = "nep+eng" if ("mixed" in stem or "bilingual" in stem) else ("nep" if "nep" in avail_langs else "eng")
                ocr_text = pytesseract.image_to_string(img, lang=case_lang, config="--psm 6")
            elif engine == "easyocr":
                raise NotImplementedError("EasyOCR evaluation requires pre-cached models in hermetic test env.")
            elif engine == "trocr":
                raise NotImplementedError("TrOCR evaluation requires local model weights in HF_HOME.")
            else:
                ocr_text = ""

        cer = compute_cer(gt_text, ocr_text)
        wer = compute_wer(gt_text, ocr_text)

        # Validate computed CER/WER metrics
        assert cer >= 0.0 and not (cer != cer), f"Invalid CER computed for {stem}: {cer}"
        assert wer >= 0.0 and not (wer != wer), f"Invalid WER computed for {stem}: {wer}"

        results.append(CaseResult(
            case_id=stem,
            description=stem.replace("_", " ").title(),
            ref_chars=len(gt_text),
            hyp_chars=len(ocr_text),
            ref_words=len(gt_text.split()),
            hyp_words=len(ocr_text.split()),
            cer=cer,
            wer=wer,
            extracted_text=ocr_text.strip(),
        ))

    total_cer = sum(r.cer for r in results)
    total_wer = sum(r.wer for r in results)
    avg_cer = total_cer / len(results) if results else 0.0
    avg_wer = total_wer / len(results) if results else 0.0

    return {
        "results": results,
        "engine": engine,
        "lang": lang_str,
        "aggregate": {
            "avg_cer": avg_cer,
            "avg_wer": avg_wer,
            "total_cases": len(results),
        },
        "dataset_type": "synthetic",
    }


def print_report(eval_data: dict):
    results: list[CaseResult] = eval_data["results"]
    engine = eval_data["engine"]
    agg = eval_data.get("aggregate", {})
    print(f"\n=======================================================")
    print(f"  hamiGenZ OCR Evaluation Benchmark — Engine: {engine} (Synthetic)")
    print(f"=======================================================\n")
    print(f"| Case ID | Description | Ref Chars | Hyp Chars | CER (%) | WER (%) |")
    print(f"|---|---|---|---|---|---|")
    for r in results:
        print(f"| `{r.case_id}` | {r.description} | {r.ref_chars} | {r.hyp_chars} | {r.cer * 100:.1f}% | {r.wer * 100:.1f}% |")
    print(f"\nAverage CER: {agg.get('avg_cer', 0.0) * 100:.1f}% | Average WER: {agg.get('avg_wer', 0.0) * 100:.1f}%\n")


if __name__ == "__main__":
    report = run_ocr_eval("tesseract")
    print_report(report)
