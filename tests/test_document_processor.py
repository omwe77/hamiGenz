"""
tests/test_document_processor.py — Resilience and boundary tests for DocumentProcessor.

Deterministic tests covering input boundaries, corrupt file handling, resource cleanup,
page limit thresholds, out-of-bounds rendering, and Unicode normalization.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz  # PyMuPDF
import pytest
from PIL import Image

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from document_processor import DocumentProcessor, Chunker, _best_ocr_lang


@pytest.fixture
def processor(tmp_path):
    upload_dir = tmp_path / "uploads"
    return DocumentProcessor(upload_dir=str(upload_dir))


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a minimal valid 2-page PDF in tmp_path with sufficient text."""
    pdf_path = tmp_path / "valid_sample.pdf"
    doc = fitz.open()
    # Page 1 (>30 chars to avoid likely_scanned trigger)
    p1 = doc.new_page(width=300, height=300)
    p1.insert_text((50, 50), "First page sample content with sufficient characters for extraction.")
    # Page 2 (>30 chars to avoid likely_scanned trigger)
    p2 = doc.new_page(width=300, height=300)
    p2.insert_text((50, 50), "Second page sample content with sufficient characters for extraction.")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def sample_image(tmp_path):
    """Create a minimal valid image in tmp_path."""
    img_path = tmp_path / "valid_sample.png"
    img = Image.new("RGB", (100, 100), color="white")
    img.save(str(img_path))
    return img_path


# ---------------------------------------------------------------------------
# 1. Input validation & corrupt file handling
# ---------------------------------------------------------------------------

class TestExtractionBoundaries:
    def test_nonexistent_file_raises_filenotfound(self, processor, tmp_path):
        fake_file = str(tmp_path / "nonexistent.pdf")
        with pytest.raises(FileNotFoundError, match="File not found"):
            processor.extract_text(fake_file)

    def test_zero_byte_pdf_raises_value_error(self, processor, tmp_path):
        empty_pdf = tmp_path / "empty.pdf"
        empty_pdf.write_bytes(b"")
        with pytest.raises(ValueError, match="File is empty"):
            processor.extract_text(str(empty_pdf))

    def test_zero_byte_image_raises_value_error(self, processor, tmp_path):
        empty_img = tmp_path / "empty.png"
        empty_img.write_bytes(b"")
        with pytest.raises(ValueError, match="File is empty"):
            processor.extract_text(str(empty_img))

    def test_unsupported_extension_raises_value_error(self, processor, tmp_path):
        bad_file = tmp_path / "file.exe"
        bad_file.write_bytes(b"binary content")
        with pytest.raises(ValueError, match="Unsupported file type"):
            processor.extract_text(str(bad_file))

    def test_corrupt_pdf_content_raises_value_error(self, processor, tmp_path):
        corrupt_pdf = tmp_path / "corrupt.pdf"
        corrupt_pdf.write_bytes(b"%PDF-1.4 header but totally corrupt garbage binary data")
        with pytest.raises(ValueError, match="Could not open PDF file"):
            processor.extract_text(str(corrupt_pdf))

    def test_corrupt_image_content_raises_value_error(self, processor, tmp_path):
        corrupt_img = tmp_path / "corrupt.png"
        corrupt_img.write_bytes(b"\x89PNG\r\n\x1a\n not a valid png body")
        with pytest.raises(ValueError, match="Could not open image file"):
            processor.extract_text(str(corrupt_img))

    def test_zero_page_pdf_raises_value_error(self, processor, tmp_path):
        dummy_pdf = tmp_path / "zero_page.pdf"
        dummy_pdf.write_bytes(b"%PDF-1.4 header")
        mock_doc = MagicMock()
        mock_doc.is_encrypted = False
        mock_doc.__len__.return_value = 0
        with patch("document_processor.fitz.open", return_value=mock_doc):
            with pytest.raises(ValueError, match="PDF contains no pages"):
                processor.extract_text(str(dummy_pdf))

    def test_max_pages_limit_exceeded_raises_value_error(self, processor, sample_pdf):
        # sample_pdf has 2 pages; setting max_pages=1 should raise ValueError
        with pytest.raises(ValueError, match="Document has too many pages"):
            processor.extract_text(str(sample_pdf), max_pages=1)


# ---------------------------------------------------------------------------
# 2. Successful extraction & source_type tracking
# ---------------------------------------------------------------------------

class TestExtractionSuccess:
    def test_extract_pdf_pages_cleanly(self, processor, sample_pdf):
        pages = processor.extract_text(str(sample_pdf))
        assert len(pages) == 2
        assert pages[0]["page_num"] == 1
        assert "First page sample content" in pages[0]["text"]
        assert pages[0]["source_type"] == "text"
        assert pages[1]["page_num"] == 2
        assert "Second page sample content" in pages[1]["text"]

    def test_extract_image_returns_single_ocr_page(self, processor, sample_image):
        with patch("document_processor._best_ocr_lang", return_value="Mocked OCR Text"):
            pages = processor.extract_text(str(sample_image))
        assert len(pages) == 1
        assert pages[0]["page_num"] == 1
        assert pages[0]["text"] == "Mocked OCR Text"
        assert pages[0]["source_type"] == "ocr"


# ---------------------------------------------------------------------------
# 3. Page rendering out-of-bounds safety
# ---------------------------------------------------------------------------

class TestPageRenderingBounds:
    def test_render_page_image_zero_or_negative_returns_none(self, processor, sample_pdf):
        assert processor.render_page_image(str(sample_pdf), 0) is None
        assert processor.render_page_image(str(sample_pdf), -1) is None

    def test_render_page_image_out_of_bounds_returns_none(self, processor, sample_pdf):
        assert processor.render_page_image(str(sample_pdf), 999) is None

    def test_render_page_image_valid_returns_bytes(self, processor, sample_pdf):
        img_bytes = processor.render_page_image(str(sample_pdf), 1)
        assert isinstance(img_bytes, bytes)
        assert img_bytes.startswith(b"\x89PNG")

    def test_render_page_pil_out_of_bounds_returns_none(self, processor, sample_pdf):
        assert processor._render_page_pil(str(sample_pdf), 0) is None
        assert processor._render_page_pil(str(sample_pdf), 5) is None

    def test_render_page_pil_valid_returns_image(self, processor, sample_pdf):
        img = processor._render_page_pil(str(sample_pdf), 1)
        assert isinstance(img, Image.Image)

    def test_word_boxes_out_of_bounds_returns_empty_list(self, processor, sample_pdf):
        assert processor._tesseract_word_boxes(str(sample_pdf), 0) == []
        assert processor._tesseract_word_boxes(str(sample_pdf), 50) == []

    def test_ocr_page_out_of_bounds_returns_empty_string(self, processor, sample_pdf):
        assert processor._ocr_page_fitx(str(sample_pdf), 0) == ""
        assert processor._ocr_page_fitx(str(sample_pdf), 50) == ""


# ---------------------------------------------------------------------------
# 4. Save upload filename neutralization
# ---------------------------------------------------------------------------

class TestSaveUpload:
    def test_path_traversal_neutralized(self, processor):
        content = b"%PDF-1.4 test"
        path_str, doc_id = processor.save_upload(content, "../../dangerous/etc/passwd.pdf")
        saved_path = Path(path_str)
        assert saved_path.parent == processor.upload_dir
        assert saved_path.name == f"{doc_id}.pdf"

    def test_custom_doc_id_validated(self, processor):
        content = b"%PDF-1.4 test"
        path_str, doc_id = processor.save_upload(content, "test.pdf", doc_id="custom-123_a")
        assert doc_id == "custom-123_a"

    def test_invalid_custom_doc_id_rejected(self, processor):
        with pytest.raises(ValueError, match="Invalid document id"):
            processor.save_upload(b"content", "test.pdf", doc_id="bad/id;drop")


# ---------------------------------------------------------------------------
# 5. Unicode and Text Cleaning
# ---------------------------------------------------------------------------

class TestTextCleaning:
    def test_unicode_nfc_normalization(self):
        import unicodedata
        # Decomposed Latin e + combining acute (U+0301) normalizes to é (U+00E9) in NFC
        decomposed = "e\u0301"
        cleaned = DocumentProcessor.clean_text(decomposed)
        assert cleaned == "\u00e9"
        # Devanagari NFC verification
        devanagari = "\u0958"
        assert DocumentProcessor.clean_text(devanagari) == unicodedata.normalize("NFC", devanagari)

    def test_whitespace_and_blank_line_collapse(self):
        raw = "Line 1   with    spaces\n\n\n\nLine 2\n\n   \nLine 3"
        cleaned = DocumentProcessor.clean_text(raw)
        assert "   " not in cleaned
        assert cleaned == "Line 1 with spaces\nLine 2\nLine 3"

    def test_empty_string(self):
        assert DocumentProcessor.clean_text("") == ""


# ---------------------------------------------------------------------------
# 6. OCR integration fallback in _best_ocr_lang
# ---------------------------------------------------------------------------

class TestBestOCRLangFallback:
    def test_delegates_to_ocr_engines_when_available(self):
        mock_img = Image.new("RGB", (50, 50), "white")
        with patch("ocr_engines.best_ocr_text", return_value="Devanagari Result"):
            result = _best_ocr_lang(mock_img)
        assert result == "Devanagari Result"

    def test_falls_back_when_ocr_engines_fails(self):
        mock_img = Image.new("RGB", (50, 50), "white")
        with patch("ocr_engines.best_ocr_text", side_effect=Exception("engine failure")), \
             patch("document_processor.get_available_languages", return_value=["eng"]), \
             patch("document_processor.pytesseract.image_to_string", return_value="Tesseract Fallback"):
            result = _best_ocr_lang(mock_img)
        assert result == "Tesseract Fallback"
