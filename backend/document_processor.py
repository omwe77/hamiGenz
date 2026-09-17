"""
hamigenz backend — Phase 1 MVP
Document Understanding Pipeline
"""

import os
import re
import uuid
import sqlite3
from pathlib import Path
from typing import Optional

import pdfplumber
import fitz  # PyMuPDF
from PIL import Image
import pytesseract


# ─── Tesseract configuration ──────────────────────────────────────
# Resolve paths relative to THIS file's location, not the CWD, so the backend
# works no matter how it is launched (uvicorn, IDE, run.sh, etc.)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_TESSERACT_BIN = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
_PROJECT_TESSDATA = _BACKEND_ROOT / "data" / "tessdata"

# Tesseract binary: env var override → Windows default → last-resort search
if "TESSERACT_BIN" in os.environ and os.environ["TESSERACT_BIN"]:
    TESSERACT_BIN = Path(os.environ["TESSERACT_BIN"])
elif _DEFAULT_TESSERACT_BIN.exists():
    TESSERACT_BIN = _DEFAULT_TESSERACT_BIN
else:
    # Fallback: try to find tesseract on PATH
    import shutil
    found = shutil.which("tesseract")
    TESSERACT_BIN = Path(found) if found else _DEFAULT_TESSERACT_BIN

# Project tessdata: env var override → project data/tessdata
if "TESSDATA_PREFIX" in os.environ and os.environ["TESSDATA_PREFIX"]:
    PROJECT_TESSDATA = Path(os.environ["TESSDATA_PREFIX"])
elif _PROJECT_TESSDATA.is_dir():
    PROJECT_TESSDATA = _PROJECT_TESSDATA
else:
    PROJECT_TESSDATA = _PROJECT_TESSDATA  # still set, OCR will fail loudly if missing

# Apply configuration once at import time
pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_BIN)
if PROJECT_TESSDATA.exists():
    os.environ["TESSDATA_PREFIX"] = str(PROJECT_TESSDATA)

# Available languages (resolved once at import)
_TESS_LANGUAGES: Optional[list[str]] = None


def get_available_languages() -> list[str]:
    """Return list of tesseract languages available in TESSDATA_PREFIX."""
    global _TESS_LANGUAGES
    if _TESS_LANGUAGES is None:
        try:
            _TESS_LANGUAGES = pytesseract.get_languages()
        except Exception:
            _TESS_LANGUAGES = []
    return _TESS_LANGUAGES


def _build_lang_string(requested: str = "eng+nep") -> str:
    """Build a lang string that only includes actually-available languages.

    Since Devanagari text is best OCR'd with the Nepali model alone
    (the English model interferes and produces garbage), prefer 'nep'
    when it's available, even if 'eng+nep' was requested.
    """
    requested_set = set(requested.split("+"))
    available = set(get_available_languages())

    # If Nepali is available, prefer it for any request that includes it
    # (Devanagari OCR works best with the Nepali-trained model alone)
    if "nep" in available and "nep" in requested_set:
        return "nep"

    usable = requested_set & available
    if not usable:
        usable = available
    if not usable:
        return "eng"
    return "+".join(sorted(usable))


def _best_ocr_lang(img) -> str:
    """Choose the best OCR result by trying multiple configs.

    For Devanagari-heavy pages, Nepali-only model usually beats
    eng+nep combined (English model garbles Devanagari). We try
    nep, eng+nep, and eng, then pick the one yielding most
    Nepali characters (better Devanagari = better for Nepali docs).
    """
    nep_range = (0x0900, 0x097F)

    def cnt(text: str) -> int:
        return sum(1 for c in text if nep_range[0] <= ord(c) <= nep_range[1])

    available = set(get_available_languages())
    results: list[tuple[str, int, str]] = []

    # Nepali-only (best for Devanagari)
    if "nep" in available:
        try:
            t = pytesseract.image_to_string(img, lang="nep", config="--psm 6")
            results.append(("nep", cnt(t), t))
        except Exception:
            pass

    # Eng+nep (mixed content)
    if "eng" in available and "nep" in available:
        try:
            t = pytesseract.image_to_string(img, lang="eng+nep", config="--psm 6")
            results.append(("eng+nep", cnt(t), t))
        except Exception:
            pass

    # Eng only (pure English fallback)
    if "eng" in available:
        try:
            t = pytesseract.image_to_string(img, lang="eng", config="--psm 6")
            results.append(("eng", cnt(t), t))
        except Exception:
            pass

    if not results:
        return ""

    # Pick the config that recognised the most Nepali characters
    best = max(results, key=lambda x: x[1])
    return best[2].strip()


class DocumentProcessor:
    """Extract text from PDFs and images with page-level tracking."""

    def __init__(self, upload_dir: str):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, file_bytes: bytes, filename: str) -> str:
        """Save uploaded file, return doc_id."""
        doc_id = str(uuid.uuid4())[:8]
        ext = Path(filename).suffix.lower()
        safe_name = f"{doc_id}{ext}"
        filepath = self.upload_dir / safe_name
        filepath.write_bytes(file_bytes)
        return str(filepath), doc_id

    def extract_text(self, filepath: str) -> list[dict]:
        """
        Extract text from PDF or image.
        Returns list of dicts: {page_num, text, source_type}
        """
        ext = Path(filepath).suffix.lower()

        if ext == ".pdf":
            return self._extract_pdf(filepath)
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif"):
            return self._extract_image(filepath)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _extract_pdf(self, filepath: str) -> list[dict]:
        """Try text extraction first, fall back to OCR per page if needed."""
        pages = []
        doc = fitz.open(filepath)

        for i, page in enumerate(doc):
            text = page.get_text().strip()
            images = page.get_images()
            has_images = len(images) > 0

            # Heuristic: estimate if page is likely scanned (image-based)
            # A page is "likely scanned" when:
            #   - It has raster images AND very little extractable text, OR
            #   - It has zero extractable text
            char_count = len(text)
            img_area = sum(
                (img[2] or 0) * (img[3] or 0) for img in images
            )  # width * height from PyMuPDF image xrefs

            likely_scanned = (
                (char_count == 0)
                or (char_count < 80 and has_images and img_area > 50000)
                or (char_count < 30)
            )

            pages.append({
                "page_num": i + 1,
                "text": text,
                "source_type": "text" if text and not likely_scanned else "empty",
                "has_images": has_images,
                "img_area": img_area,
            })

        # Second pass: OCR pages marked as likely scanned
        for p in pages:
            if p["source_type"] == "empty":
                ocr_text = self._ocr_page_fitx(filepath, p["page_num"])
                if ocr_text and len(ocr_text.strip()) > len(p["text"].strip()):
                    p["text"] = ocr_text
                    p["source_type"] = "ocr"

        doc.close()
        return pages

    def render_page_image(self, filepath: str, page_num: int) -> bytes | None:
        """
        Render a single PDF page to PNG bytes for the document viewer.
        Returns None if the page cannot be rendered.
        """
        try:
            doc = fitz.open(filepath)
            page = doc[page_num - 1]
            mat = fitz.Matrix(200/72, 200/72)  # 200 DPI for viewer display
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            doc.close()
            return img_bytes
        except Exception as e:
            print(f"render_page_image failed for {filepath} page {page_num}: {e}")
            return None


    def _ocr_page_fitx(self, filepath: str, page_num: int) -> str:
        """OCR a single PDF page using PyMuPDF rendering + Tesseract.

        Tries multiple OCR configurations and picks the best result
        (most Nepali characters = better Devanagari recognition).
        """
        try:
            doc = fitz.open(filepath)
            page = doc[page_num - 1]
            # Render at 300 DPI for OCR quality
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()

            result = _best_ocr_lang(img)
            return result if result else ""
        except Exception as e:
            print(f"OCR failed for page {page_num}: {e}")
            return ""

    def _extract_image(self, filepath: str) -> list[dict]:
        """OCR a single image file, trying multiple configs."""
        img = Image.open(filepath)
        result = _best_ocr_lang(img)
        return [{"page_num": 1, "text": result if result else "", "source_type": "ocr"}]

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean extracted text: normalize whitespace, fix common OCR issues."""
        # Normalize Unicode
        text = text.normalize("NFC") if hasattr(text, "normalize") else text
        # Collapse multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Remove excessive spaces
        text = re.sub(r"[ \t]+", " ", text)
        # Trim lines
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(line for line in lines if line)
        return text


class Chunker:
    """Split documents into retrievable chunks with metadata."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_pages(self, pages: list[dict], doc_id: str, filename: str) -> list[dict]:
        """
        Convert pages to chunks.
        Each chunk: {doc_id, chunk_id, page_num, text, filename, index}
        """
        chunks = []
        chunk_index = 0

        for page in pages:
            text = page["text"]
            if not text or len(text.strip()) < 20:
                continue

            cleaned = DocumentProcessor.clean_text(text)
            if len(cleaned) < 20:
                continue

            # Split into sentences for smarter chunking
            sentences = self._split_sentences(cleaned)
            current_chunk = []
            current_len = 0

            for sent in sentences:
                sent_len = len(sent)
                if current_len + sent_len > self.chunk_size and current_chunk:
                    # Emit chunk
                    chunk_text = " ".join(current_chunk)
                    chunks.append({
                        "doc_id": doc_id,
                        "chunk_id": f"{doc_id}_chunk_{chunk_index}",
                        "page_num": page["page_num"],
                        "text": chunk_text,
                        "filename": filename,
                        "source_type": page.get("source_type", "unknown"),
                        "index": chunk_index,
                    })
                    chunk_index += 1
                    # Overlap: keep last few sentences
                    overlap_sents = current_chunk[-max(1, self.overlap // 20):]
                    current_chunk = overlap_sents
                    current_len = sum(len(s) for s in current_chunk)
                current_chunk.append(sent)
                current_len += sent_len

            # Emit remaining
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_chunk_{chunk_index}",
                    "page_num": page["page_num"],
                    "text": chunk_text,
                    "filename": filename,
                    "source_type": page.get("source_type", "unknown"),
                    "index": chunk_index,
                })
                chunk_index += 1

        return chunks

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentence-like units."""
        # Handle Nepali and English sentence endings
        sentences = re.split(r'(?<=[।!?.,])\s+', text)
        return [s.strip() for s in sentences if s.strip()]


class MetadataStore:
    """SQLite store for document metadata and chunk registry."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                page_count INTEGER DEFAULT 0,
                language_hint TEXT,
                source_type TEXT DEFAULT 'unknown'
            );
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                page_num INTEGER,
                text TEXT,
                source_type TEXT,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS qa_sessions (
                session_id TEXT PRIMARY KEY,
                doc_id TEXT,
                query TEXT,
                answer TEXT,
                created_at TEXT
            );
        """)
        conn.commit()
        conn.close()

    def add_document(self, doc_id: str, filename: str, filepath: str,
                     page_count: int, language_hint: str = "") -> None:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT INTO documents (doc_id, filename, filepath, upload_date, page_count, language_hint) VALUES (?,?,?,?,?,?)",
            (doc_id, filename, filepath, __import__('datetime').datetime.now().isoformat(),
             page_count, language_hint)
        )
        conn.commit()
        conn.close()

    def add_chunks(self, chunks: list[dict]) -> None:
        conn = sqlite3.connect(str(self.db_path))
        conn.executemany(
            "INSERT INTO chunks (chunk_id, doc_id, page_num, text, source_type) VALUES (?,?,?,?,?)",
            [(c["chunk_id"], c["doc_id"], c["page_num"], c["text"], c["source_type"]) for c in chunks]
        )
        conn.commit()
        conn.close()

    def get_document(self, doc_id: str) -> Optional[dict]:
        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute(
            "SELECT * FROM documents WHERE doc_id=?", (doc_id,)
        ).fetchone()
        conn.close()
        if row:
            return {
                "doc_id": row[0], "filename": row[1], "filepath": row[2],
                "upload_date": row[3], "page_count": row[4], "language_hint": row[5]
            }
        return None

    def delete_document(self, doc_id: str) -> None:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
        conn.commit()
        conn.close()

    def list_documents(self) -> list[dict]:
        conn = sqlite3.connect(str(self.db_path))
        rows = conn.execute("SELECT * FROM documents ORDER BY upload_date DESC").fetchall()
        conn.close()
        return [{
            "doc_id": r[0], "filename": r[1], "filepath": r[2],
            "upload_date": r[3], "page_count": r[4], "language_hint": r[5]
        } for r in rows]
