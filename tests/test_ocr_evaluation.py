"""
Regression and verification test for OCR evaluation corpus and benchmark.
"""
from pathlib import Path
import pytest
from tests.evaluation.eval_ocr import run_ocr_eval, CORPUS_DIR


def test_ocr_corpus_files_exist_and_paired():
    """Validate image/ground-truth pairing and non-emptiness."""
    assert CORPUS_DIR.exists(), "Corpus directory should exist"
    pngs = sorted(CORPUS_DIR.glob("*.png"))
    gts = sorted(CORPUS_DIR.glob("*.gt.txt"))
    assert len(pngs) >= 5, f"Expected at least 5 images, found {len(pngs)}"
    assert len(gts) >= 5, f"Expected at least 5 ground-truth files, found {len(gts)}"

    for png in pngs:
        matching_gt = CORPUS_DIR / f"{png.stem}.gt.txt"
        assert matching_gt.exists(), f"Missing ground truth for {png.name}"
        gt_content = matching_gt.read_text(encoding="utf-8").strip()
        assert len(gt_content) > 10, f"Ground truth for {png.name} is suspiciously short or empty"


def test_ocr_unsupported_engine_rejected():
    """Unsupported OCR engine must be explicitly rejected, not return empty text."""
    with pytest.raises(ValueError, match="Unsupported OCR engine"):
        run_ocr_eval(engine="non_existent_engine")


def test_ocr_benchmark_run():
    """Verify execution of benchmark runner and presence of aggregate metrics."""
    report = run_ocr_eval(engine="tesseract")
    results = report["results"]
    assert len(results) >= 5, "Expected results for at least 5 benchmark cases"
    assert "aggregate" in report, "Report must include aggregate metrics"
    assert "avg_cer" in report["aggregate"]
    assert "avg_wer" in report["aggregate"]
    assert report["dataset_type"] == "synthetic"

    for r in results:
        assert r.hyp_chars > 0, f"Hypothesis text was empty for {r.case_id}"
        assert r.hyp_chars >= int(r.ref_chars * 0.4), f"Hypothesis too short for {r.case_id}"
        assert r.cer >= 0.0
        assert r.wer >= 0.0


def test_ocr_benchmark_regression_thresholds():
    """
    Establish meaningful regression thresholds from actual measured baseline results.
    Prevents regressions in Tesseract Devanagari/English extraction.
    Baseline (Tesseract 5.4.0 nep+eng):
      01_digital_clean: ~17.2% CER
      02_scanned_noise: ~10.8% CER
      03_lowres_blur:   ~14.2% CER
      04_rotated_skew:  ~15.3% CER
      05_mixed_bilingual: ~2.2% CER
      Aggregate avg CER: ~12.0%
    """
    report = run_ocr_eval(engine="tesseract")
    res_map = {r.case_id: r for r in report["results"]}

    # Bilingual case is high accuracy
    assert res_map["05_mixed_bilingual"].cer <= 0.10, (
        f"Regression in bilingual OCR: {res_map['05_mixed_bilingual'].cer:.3f} > 0.10"
    )

    # Scanned noise handled well
    assert res_map["02_scanned_noise"].cer <= 0.25, (
        f"Regression in scanned noise OCR: {res_map['02_scanned_noise'].cer:.3f} > 0.25"
    )

    # Synthetic Devanagari cases
    for case_id in ("01_digital_clean", "03_lowres_blur", "04_rotated_skew"):
        assert res_map[case_id].cer <= 0.35, (
            f"Regression in {case_id} OCR: {res_map[case_id].cer:.3f} > 0.35"
        )

    # Overall aggregate CER ceiling
    avg_cer = report["aggregate"]["avg_cer"]
    assert avg_cer <= 0.25, f"Aggregate CER regressed: {avg_cer:.3f} > 0.25"