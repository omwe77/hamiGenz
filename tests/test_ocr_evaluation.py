"""
Regression and verification test for OCR evaluation corpus.
"""
from pathlib import Path
import pytest
from tests.evaluation.eval_ocr import run_ocr_eval, CORPUS_DIR


def test_ocr_corpus_files_exist():
    assert CORPUS_DIR.exists(), "Corpus directory should exist"
    pngs = list(CORPUS_DIR.glob("*.png"))
    gts = list(CORPUS_DIR.glob("*.gt.txt"))
    assert len(pngs) >= 5, f"Expected at least 5 images, found {len(pngs)}"
    assert len(gts) >= 5, f"Expected at least 5 ground-truth files, found {len(gts)}"


def test_ocr_benchmark_run():
    report = run_ocr_eval(engine="tesseract")
    results = report["results"]
    assert len(results) >= 5, "Expected results for at least 5 benchmark cases"

    for r in results:
        assert r.hyp_chars > 0, f"Hypothesis text was empty for {r.case_id}"
        # Hypothesis should capture text with reasonable character counts
        assert r.hyp_chars >= int(r.ref_chars * 0.4), f"Hypothesis too short for {r.case_id}"
