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
        needs_ocr = False

        # First pass: try text extraction
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            if text:
                pages.append({
                    "page_num": i + 1,
                    "text": text,
                    "source_type": "text",
                    "has_images": len(page.get_images()) > 0,
                })
            else:
                needs_ocr = True
                pages.append({
                    "page_num": i + 1,
                    "text": "",
                    "source_type": "empty",
                    "has_images": len(page.get_images()) > 0,
                })

        # Second pass: OCR empty pages or pages with images but no text
        if needs_ocr:
            for p in pages:
                if p["source_type"] in ("empty",) or (
                    p["source_type"] == "text" and len(p["text"]) < 50 and p["has_images"]
                ):
                    ocr_text = self._ocr_page_fitx(filepath, p["page_num"])
                    if ocr_text:
                        p["text"] = ocr_text
                        p["source_type"] = "ocr"

        doc.close()
        return pages

    def _ocr_page_fitx(self, filepath: str, page_num: int) -> str:
        """OCR a single PDF page using PyMuPDF rendering + Tesseract."""
        try:
            doc = fitz.open(filepath)
            page = doc[page_num - 1]
            # Render at 300 DPI for OCR quality
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
            text = pytesseract.image_to_string(img, lang="eng+nep")
            return text.strip()
        except Exception as e:
            print(f"OCR failed for page {page_num}: {e}")
            return ""

    def _extract_image(self, filepath: str) -> list[dict]:
        """OCR a single image file."""
        img = Image.open(filepath)
        text = pytesseract.image_to_string(img, lang="eng+nep")
        return [{"page_num": 1, "text": text.strip(), "source_type": "ocr"}]

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
