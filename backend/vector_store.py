"""
hamigenz — Embedding Service + Vector Storage (FAISS)
"""
import os
import json
import re
import uuid
from pathlib import Path
from typing import Optional

import faiss
import numpy as np

from sentence_transformers import SentenceTransformer

from document_processor import Chunker


class EmbeddingService:
    """Generate embeddings using a local free model."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self._load_model()

    def _load_model(self):
        print(f"[EmbeddingService] Loading model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        print(f"[EmbeddingService] Model loaded. Embedding dim: {self.model.get_sentence_embedding_dimension()}")

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """Embed a list of texts. Returns numpy array (n, dim)."""
        if not texts:
            return np.array([]).reshape(0, self.model.get_sentence_embedding_dimension())
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.astype(np.float32)

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text."""
        return self.embed_texts([text])

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()


class VectorStore:
    """FAISS-based vector storage with document isolation."""

    def __init__(self, vectors_dir: str, dimension: int):
        self.vectors_dir = Path(vectors_dir)
        self.vectors_dir.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension
        self._doc_indices: dict[str, str] = {}  # doc_id -> index filepath
        self._load_registry()

    def _load_registry(self):
        """Load registry of existing doc indices."""
        registry_path = self.vectors_dir / "registry.json"
        if registry_path.exists():
            with open(registry_path, encoding="utf-8") as f:
                self._doc_indices = json.load(f)

    def _stamp_path(self) -> Path:
        return self.vectors_dir / "embed_model.txt"

    def check_model_stamp(self, model_name: str) -> dict:
        """Compare the stored embedding-model stamp with the active model.

        The stamp prevents silent vector corruption: two different models
        can share the same dimension (e.g. all-MiniLM-L6-v2 and
        paraphrase-multilingual-MiniLM-L12-v2 are both 384-dim), so a
        dimension check alone cannot detect a model switch.

        Returns {current, stored, reindex_chunks, missing} where
        reindex_chunks lists doc_ids whose stored chunks can be re-embedded
        from chunk metadata alone (no original file needed).
        """
        stored = None
        if self._stamp_path().exists():
            stored = self._stamp_path().read_text(encoding="utf-8").strip()
        reindexable = []
        if stored and stored != model_name:
            for doc_id in self._doc_indices:
                meta_path = self.vectors_dir / f"{doc_id}_meta.json"
                if meta_path.exists():
                    try:
                        with open(meta_path, encoding="utf-8") as f:
                            chunks = json.load(f)
                        if chunks and all("text" in c for c in chunks):
                            reindexable.append(doc_id)
                    except (json.JSONDecodeError, OSError):
                        pass
        return {
            "current": model_name,
            "stored": stored,
            "reindex_chunks": reindexable,
            "missing": stored is None,
        }

    def write_model_stamp(self, model_name: str) -> None:
        self._stamp_path().write_text(model_name, encoding="utf-8")

    @staticmethod
    def sanitize_chunk_text(text: str) -> str:
        """Ensure chunk text is embeddable: non-empty and str-typed."""
        if not isinstance(text, str):
            return ""
        text = re.sub(r"\\s+", " ", text).strip()
        return text if text else "(empty chunk)"

    def reindex_document(self, doc_id: str, embedder,
                         batch_size: int = 32) -> dict:
        """Re-embed a document's chunks with a new model, in place.

        Reads chunk text from stored metadata (works even if the original
        upload is gone), re-embeds, and replaces the FAISS index.
        """
        meta_path = self.vectors_dir / f"{doc_id}_meta.json"
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        texts = [self.sanitize_chunk_text(c.get("text", "")) for c in meta]
        embeddings = embedder.embed_texts(texts, batch_size=batch_size)
        index = faiss.IndexFlatIP(embedder.dimension)
        index.add(embeddings.astype(np.float32))
        faiss.write_index(index, str(self.vectors_dir / f"{doc_id}.faiss"))
        return {"doc_id": doc_id, "chunks": len(meta)}

    def _save_registry(self):
        registry_path = self.vectors_dir / "registry.json"
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(self._doc_indices, f, indent=2)

    def add_document(self, doc_id: str, chunks: list[dict],
                     embeddings: np.ndarray) -> None:
        """
        Create a FAISS index for a document and store it.
        chunks: list of chunk dicts with chunk_id
        embeddings: (n_chunks, dim) array
        """
        if doc_id in self._doc_indices:
            self.remove_document(doc_id)

        index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine with normalized vectors)
        index.add(embeddings)

        # Save index
        index_path = self.vectors_dir / f"{doc_id}.faiss"
        faiss.write_index(index, str(index_path))

        # Save chunk metadata alongside
        meta_path = self.vectors_dir / f"{doc_id}_meta.json"
        meta = [
            {
                "chunk_id": c["chunk_id"],
                "page_num": c["page_num"],
                "text": c["text"],
                "source_type": c["source_type"],
                "filename": c["filename"],
            }
            for c in chunks
        ]
        # encoding='utf-8' is REQUIRED: chunk text is frequently Nepali and
        # the Windows default (cp1252) cannot encode Devanagari.
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        self._doc_indices[doc_id] = str(index_path)
        self._save_registry()

    def search(self, doc_id: str, query_embedding: np.ndarray,
               top_k: int = 5) -> list[dict]:
        """
        Search a specific document's index.
        Returns list of {chunk_id, page_num, text, score, filename}
        """
        if doc_id not in self._doc_indices:
            return []

        index_path = self._doc_indices[doc_id]
        if not Path(index_path).exists():
            return []

        index = faiss.read_index(index_path)
        query_vec = query_embedding.astype(np.float32).reshape(1, -1)

        scores, ids = index.search(query_vec, top_k)

        # Load metadata
        meta_path = self.vectors_dir / f"{doc_id}_meta.json"
        if not meta_path.exists():
            return []

        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx >= len(meta):
                continue
            results.append({
                "chunk_id": meta[idx]["chunk_id"],
                "page_num": meta[idx]["page_num"],
                "text": meta[idx]["text"],
                "score": float(score),
                "filename": meta[idx]["filename"],
                "source_type": meta[idx]["source_type"],
            })

        return results

    def search_all(self, query_embedding: np.ndarray,
                   top_k: int = 5, min_score: float = 0.10) -> list[dict]:
        """
        Search across all documents.
        Returns merged results with doc_id.
        """
        all_results = []
        query_vec = query_embedding.astype(np.float32).reshape(1, -1)

        for doc_id, index_path in self._doc_indices.items():
            if not Path(index_path).exists():
                continue
            index = faiss.read_index(index_path)
            scores, ids = index.search(query_vec, top_k)

            meta_path = self.vectors_dir / f"{doc_id}_meta.json"
            if not meta_path.exists():
                continue
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)

            for score, idx in zip(scores[0], ids[0]):
                if idx >= len(meta):
                    continue
                if float(score) < min_score:
                    continue
                all_results.append({
                    "doc_id": doc_id,
                    "chunk_id": meta[idx]["chunk_id"],
                    "page_num": meta[idx]["page_num"],
                    "text": meta[idx]["text"],
                    "score": float(score),
                    "filename": meta[idx]["filename"],
                    "source_type": meta[idx]["source_type"],
                })

        # Sort by score descending, take top_k
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:top_k]

    def remove_document(self, doc_id: str) -> None:
        """Remove a document's index and metadata."""
        if doc_id in self._doc_indices:
            del self._doc_indices[doc_id]
            self._save_registry()

        index_path = self.vectors_dir / f"{doc_id}.faiss"
        if index_path.exists():
            index_path.unlink()

        meta_path = self.vectors_dir / f"{doc_id}_meta.json"
        if meta_path.exists():
            meta_path.unlink()


class Pipeline:
    """End-to-end document processing pipeline."""

    def __init__(self, embedding_service: EmbeddingService,
                 vector_store: VectorStore,
                 chunker: Chunker,
                 metadata_store):
        self.embedder = embedding_service
        self.vector_store = vector_store
        self.chunker = chunker
        self.metadata = metadata_store

    def process_document(self, filepath: str, doc_id: str,
                         filename: str) -> dict:
        """
        Full pipeline: extract → chunk → embed → store.
        Returns processing summary.
        """
        from document_processor import DocumentProcessor
        processor = DocumentProcessor(upload_dir="")  # filepath already saved

        # Extract
        pages = processor.extract_text(filepath)
        page_count = len(pages)

        # Detect language hint
        language_hint = self._detect_language_hint(pages)

        # Chunk
        chunks = self.chunker.chunk_pages(pages, doc_id, filename)

        if not chunks:
            return {"status": "error", "message": "No extractable text found in document."}

        # Embed
        texts = [c["text"] for c in chunks]
        embeddings = self.embedder.embed_texts(texts)

        # Store
        self.vector_store.add_document(doc_id, chunks, embeddings)
        self.metadata.add_document(doc_id, filename, filepath,
                                   page_count, language_hint)
        self.metadata.add_chunks(chunks)

        return {
            "status": "success",
            "doc_id": doc_id,
            "filename": filename,
            "pages": page_count,
            "chunks": len(chunks),
            "language_hint": language_hint,
        }

    def query(self, doc_id: str | None, question: str,
              top_k: int = 5, min_score: float = 0.10) -> list[dict]:
        """Retrieve relevant chunks for a question."""
        query_emb = self.embedder.embed_text(question)

        if doc_id:
            results = self.vector_store.search(doc_id, query_emb, top_k)
        else:
            results = self.vector_store.search_all(query_emb, top_k)

        return results

    @staticmethod
    def _detect_language_hint(pages: list[dict]) -> str:
        """Simple language detection hint based on script presence."""
        all_text = " ".join(p["text"] for p in pages if p["text"])
        if not all_text:
            return "unknown"

        nepali_chars = sum(1 for c in all_text if '\u0900' <= c <= '\u097F')
        total = len(all_text)

        if total == 0:
            return "unknown"

        ratio = nepali_chars / total
        if ratio > 0.3:
            return "nepali"
        elif ratio > 0.05:
            return "mixed"
        return "english"
