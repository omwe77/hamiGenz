"""
hamigenz — Embedding Service + Vector Storage (FAISS)
"""
import os
import json
import re
import uuid
import time
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

    def __init__(self, vectors_dir: str, dimension: int, metadata_store=None):
        self.vectors_dir = Path(vectors_dir)
        self.vectors_dir.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension
        self.metadata_store = metadata_store
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

    def resolve_active_paths(self, doc_id: str) -> tuple[Optional[Path], Optional[Path]]:
        """Resolve active (faiss_path, meta_path) consistently with authoritative SQLite generation.

        Handles:
        - Generation N > 0: requires {doc_id}_g{N}.faiss and {doc_id}_g{N}_meta.json
        - Generation 0 / legacy: supports {doc_id}_g0.* and {doc_id}.*
        - Missing active-generation files: explicitly logs warning and returns (None, None)
        """
        target_gen = None
        if hasattr(self, "metadata_store") and self.metadata_store is not None:
            try:
                target_gen = self.metadata_store.get_reindex_generation(doc_id)
            except Exception:
                target_gen = None

        if target_gen is not None and target_gen > 0:
            gen_faiss = self.vectors_dir / f"{doc_id}_g{target_gen}.faiss"
            gen_meta = self.vectors_dir / f"{doc_id}_g{target_gen}_meta.json"
            if gen_faiss.exists() and gen_meta.exists():
                if self._doc_indices.get(doc_id) != str(gen_faiss):
                    self._doc_indices[doc_id] = str(gen_faiss)
                return gen_faiss, gen_meta
            else:
                # Active generation files are missing!
                print(f"[VectorStore] WARNING: Active generation {target_gen} files missing for {doc_id}")
                return None, None

        # Check for generation 0 files
        g0_faiss = self.vectors_dir / f"{doc_id}_g0.faiss"
        g0_meta = self.vectors_dir / f"{doc_id}_g0_meta.json"
        if g0_faiss.exists() and g0_meta.exists():
            if self._doc_indices.get(doc_id) != str(g0_faiss):
                self._doc_indices[doc_id] = str(g0_faiss)
            return g0_faiss, g0_meta

        # Fallback to legacy flat naming
        flat_faiss = self.vectors_dir / f"{doc_id}.faiss"
        flat_meta = self.vectors_dir / f"{doc_id}_meta.json"
        if flat_faiss.exists() and flat_meta.exists():
            if self._doc_indices.get(doc_id) != str(flat_faiss):
                self._doc_indices[doc_id] = str(flat_faiss)
            return flat_faiss, flat_meta

        # Check existing entry in _doc_indices if present
        idx = self._doc_indices.get(doc_id)
        if idx:
            p = Path(idx)
            if p.exists():
                m = p.with_name(p.stem + "_meta.json") if p.name.endswith(".faiss") else None
                if m and m.exists():
                    return p, m

        return None, None

    def search(self, doc_id: str, query_embedding: np.ndarray,
               top_k: int = 5) -> list[dict]:
        """
        Search a specific document's active index and matching generation metadata.
        Returns list of {chunk_id, page_num, text, score, filename}
        """
        faiss_path, meta_path = self.resolve_active_paths(doc_id)
        if not faiss_path or not meta_path:
            return []

        index = faiss.read_index(str(faiss_path))
        query_vec = query_embedding.astype(np.float32).reshape(1, -1)

        scores, ids = index.search(query_vec, top_k)

        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0 or idx >= len(meta):
                continue
            results.append({
                "chunk_id": meta[idx]["chunk_id"],
                "page_num": meta[idx]["page_num"],
                "text": meta[idx]["text"],
                "score": float(score),
                "filename": meta[idx].get("filename", ""),
                "source_type": meta[idx].get("source_type", "unknown"),
            })

        return results

    def search_all(self, query_embedding: np.ndarray,
                   top_k: int = 5, min_score: float = 0.10) -> list[dict]:
        """
        Search across all documents using active generation indexes and metadata.
        Returns merged results with doc_id.
        """
        all_results = []
        query_vec = query_embedding.astype(np.float32).reshape(1, -1)

        if hasattr(self, "metadata_store") and self.metadata_store is not None:
            try:
                doc_ids = [d["doc_id"] for d in self.metadata_store.list_all_documents()]
            except Exception:
                doc_ids = list(self._doc_indices.keys())
        else:
            doc_ids = list(self._doc_indices.keys())

        for doc_id in doc_ids:
            faiss_path, meta_path = self.resolve_active_paths(doc_id)
            if not faiss_path or not meta_path:
                continue
            index = faiss.read_index(str(faiss_path))
            scores, ids = index.search(query_vec, top_k)

            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)

            for score, idx in zip(scores[0], ids[0]):
                if idx < 0 or idx >= len(meta):
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

    def search_documents(self, doc_ids: list[str], query_embedding: np.ndarray,
                         top_k: int = 5, min_score: float = 0.10) -> list[dict]:
        """
        Search only across the specified authorized document IDs using active generation artifacts.
        Prevents cross-user / cross-session vector search leakage.
        """
        if not doc_ids:
            return []

        all_results = []
        query_vec = query_embedding.astype(np.float32).reshape(1, -1)
        allowed_set = set(doc_ids)

        for doc_id in allowed_set:
            faiss_path, meta_path = self.resolve_active_paths(doc_id)
            if not faiss_path or not meta_path:
                continue
            index = faiss.read_index(str(faiss_path))
            scores, ids = index.search(query_vec, top_k)

            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)

            for score, idx in zip(scores[0], ids[0]):
                if idx < 0 or idx >= len(meta):
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

        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:top_k]

    def get_chunk_texts(self, doc_id: str) -> list[str]:
        """Return the stored text for every chunk of a document from active generation metadata.

        Used by the hybrid retriever to rebuild the BM25 index without
        re-reading the original upload file.
        """
        _, meta_path = self.resolve_active_paths(doc_id)
        if not meta_path or not meta_path.exists():
            return []
        import json
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        return [m.get("text", "") or "" for m in meta]

    def add_document_to_path(
        self,
        doc_id: str,
        faiss_path: Path,
        meta_path: Path,
        chunks: list[dict],
        embeddings,
    ) -> None:
        """Write a FAISS index and chunk-meta JSON to explicit (staging) paths.

        Does NOT update _doc_indices or registry.json — the caller decides
        when to make these paths the active generation (via swap_document).
        Used by the staged reindex flow (Task 2.1.2).
        """
        index = faiss.IndexFlatIP(self.dimension)
        index.add(embeddings)
        faiss.write_index(index, str(faiss_path))
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
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def swap_document(
        self,
        doc_id: str,
        new_faiss_path: Path,
        old_faiss_path: Path,
        old_meta_path: Path,
    ) -> None:
        """Point _doc_indices at the new generation's FAISS file and discard old files.

        Called after the SQLite commit succeeds so the in-memory registry
        matches the durable generation pointer.  Old files are unlinked
        post-commit; any OSError is logged and swallowed (startup scavenger
        will clean up on next boot).
        Used by the staged reindex flow (Task 2.1.2).
        """
        self._doc_indices[doc_id] = str(new_faiss_path)
        self._save_registry()
        for path in (old_faiss_path, old_meta_path):
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                print(f"[VectorStore] swap_document: could not remove {path}: {exc}")

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


class ProcessingTimeoutError(RuntimeError):
    """Raised when document processing exceeds its deadline before persistence begins."""
    pass


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
        if hasattr(self.vector_store, "metadata_store") and self.vector_store.metadata_store is None:
            self.vector_store.metadata_store = metadata_store

    def process_document(self, filepath: str, doc_id: str,
                         filename: str, session_id: str = "__anonymous__",
                         deadline: float | None = None) -> dict:
        """
        Full pipeline: extract → chunk → embed → store.
        Returns processing summary.
        If a deadline is specified, checks deadline after extraction, chunking,
        and embedding stages and aborts before persistence if exceeded.
        """
        from document_processor import DocumentProcessor
        processor = DocumentProcessor(upload_dir="")  # filepath already saved

        def _check_deadline(stage: str):
            if deadline is not None and time.monotonic() > deadline:
                raise ProcessingTimeoutError(
                    f"Document processing deadline exceeded after stage: {stage}"
                )

        _check_deadline("start")

        # Extract
        pages = processor.extract_text(filepath)
        page_count = len(pages)
        _check_deadline("extraction")

        # Detect language hint
        language_hint = self._detect_language_hint(pages)

        # Chunk
        chunks = self.chunker.chunk_pages(pages, doc_id, filename)
        _check_deadline("chunking")

        if not chunks:
            return {"status": "error", "message": "No extractable text found in document."}

        # Embed
        texts = [c["text"] for c in chunks]
        embeddings = self.embedder.embed_texts(texts)
        _check_deadline("embedding")

        # Store
        try:
            self.vector_store.add_document(doc_id, chunks, embeddings)
            self.metadata.add_document(doc_id, filename, filepath,
                                       page_count, language_hint, session_id=session_id)
            self.metadata.add_chunks(chunks)
        except Exception:
            # Atomic rollback on partial failure during persistence
            try:
                self.vector_store.remove_document(doc_id)
            except Exception:
                pass
            try:
                self.metadata.delete_document(doc_id, session_id=session_id)
            except Exception:
                pass
            raise

        return {
            "status": "success",
            "doc_id": doc_id,
            "filename": filename,
            "pages": page_count,
            "chunks": len(chunks),
            "language_hint": language_hint,
        }

    def process_document_staged(
        self,
        filepath: str,
        doc_id: str,
        filename: str,
        session_id: str,
        new_gen: int,
        faiss_path: Path,
        meta_json_path: Path,
        deadline: float | None = None,
        expected_gen: int | None = None,
    ) -> dict:
        """Extract → chunk → embed → persist to generation-specific paths.

        Identical to process_document up through embedding; then writes FAISS
        to faiss_path/meta_json_path via add_document_to_path, and commits
        SQLite via metadata.commit_reindex — the single durable commit point.
        Used by the safe staged reindex flow (Task 2.1.2).
        """
        from document_processor import DocumentProcessor
        processor = DocumentProcessor(upload_dir="")

        def _check_deadline(stage: str):
            if deadline is not None and time.monotonic() > deadline:
                raise ProcessingTimeoutError(
                    f"Reindex deadline exceeded after stage: {stage}"
                )

        _check_deadline("start")
        pages = processor.extract_text(filepath)
        page_count = len(pages)
        _check_deadline("extraction")

        # Page-limit enforcement (Task 2.1.2-E2): Reject oversized documents BEFORE any commit
        if page_count > 200:
            return {
                "status": "error",
                "message": "Document has too many pages (max 200).",
                "pages": page_count,
            }

        language_hint = self._detect_language_hint(pages)
        chunks = self.chunker.chunk_pages(pages, doc_id, filename)
        _check_deadline("chunking")
        if not chunks:
            return {"status": "error", "message": "No extractable text found in document."}
        texts = [c["text"] for c in chunks]
        embeddings = self.embedder.embed_texts(texts)
        _check_deadline("embedding")

        # Persist: write staged FAISS, then atomic SQLite commit
        try:
            self.vector_store.add_document_to_path(
                doc_id, faiss_path, meta_json_path, chunks, embeddings
            )
            self.metadata.commit_reindex(
                doc_id=doc_id,
                new_gen=new_gen,
                filename=filename,
                filepath=filepath,
                page_count=page_count,
                language_hint=language_hint,
                chunks=chunks,
                expected_gen=expected_gen if expected_gen is not None else (new_gen - 1),
            )
            # Immediate post-commit activation: swap FAISS registry and discard old files
            # Runs inside worker thread so cancellation of route coroutine cannot prevent activation
            old_faiss = self.vector_store.vectors_dir / f"{doc_id}_g{new_gen - 1}.faiss"
            if not old_faiss.exists():
                old_faiss = self.vector_store.vectors_dir / f"{doc_id}.faiss"
            old_meta = self.vector_store.vectors_dir / f"{doc_id}_g{new_gen - 1}_meta.json"
            if not old_meta.exists():
                old_meta = self.vector_store.vectors_dir / f"{doc_id}_meta.json"
            self.vector_store.swap_document(
                doc_id=doc_id,
                new_faiss_path=faiss_path,
                old_faiss_path=old_faiss,
                old_meta_path=old_meta,
            )
        except Exception:
            # Rollback: remove staged FAISS artifacts; old generation intact
            try:
                faiss_path.unlink(missing_ok=True)
            except OSError:
                pass
            try:
                meta_json_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

        return {
            "status": "success",
            "doc_id": doc_id,
            "filename": filename,
            "pages": page_count,
            "chunks": len(chunks),
            "language_hint": language_hint,
        }

    def query(self, doc_id: str | None, question: str,

              allowed_doc_ids: list[str] | None = None,
              top_k: int = 5, min_score: float = 0.10) -> list[dict]:
        """
        Retrieve relevant chunks for a question.
        Enforces that queries only access authorized document IDs for the active session.
        """
        query_emb = self.embedder.embed_text(question)

        if doc_id:
            # If allowed_doc_ids is provided, ensure doc_id is among them
            if allowed_doc_ids is not None and doc_id not in set(allowed_doc_ids):
                return []
            results = self.vector_store.search(doc_id, query_emb, top_k)
        else:
            # If doc_id is None, search ONLY across allowed_doc_ids
            if not allowed_doc_ids:
                return []
            results = self.vector_store.search_documents(allowed_doc_ids, query_emb, top_k, min_score)

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
