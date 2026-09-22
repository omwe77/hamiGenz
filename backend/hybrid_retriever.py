"""
hamigenz — Hybrid Retrieval: BM25 + Dense + RRF Fusion + Reranking

Two-stage retrieval pipeline based on 2025–2026 production RAG evidence:

- Hybrid retrieval (BM25 keyword + dense semantic) fused with Reciprocal Rank
  Fusion consistently improves precision 26–31% over pure dense retrieval and
  outperforms single-stage methods on exact keywords, serial numbers, legal
  terms — precisely the cases where embeddings blur the token you need.
- Post-retrieval reranking (here: lexical overlap scorer; plug-compatible with
  a neural CrossEncoder) fixes "right chunk retrieved but buried below noise"
  — a recall problem and a ranking problem have different fixes.

Reference pattern: BM25 + Dense → RRF fusion → rerank → top_k.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Optional

import numpy as np

from rank_bm25 import BM25Okapi


# ── Tokenisation (shared by BM25 index and lexical reranker) ──────────────────

_NEPALI_RE = re.compile(r"[\u0900-\u097F]+")
_LATIN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    """Lower-case Latin tokens + keep each Devanagari word as one token.

    Devanagari is not segmented by whitespace the way Latin is, and splitting
    on every character would blow up the index.  We keep each contiguous
    Devanagari run as one token and lower-case the Latin runs.
    """
    out: list[str] = []
    pos = 0
    while pos < len(text):
        m = _NEPALI_RE.match(text, pos)
        if m:
            out.append(m.group().lower())
            pos = m.end()
        else:
            m = _LATIN_RE.match(text, pos)
            if m:
                out.append(m.group().lower())
                pos = m.end()
            else:
                pos += 1
    return out


def _token_set(tokens: list[str]) -> Counter:
    return Counter(tokens)


# ── Lexical overlap reranker ───────────────────────────────────────────────────

class LexicalReranker:
    """Two-stage reranking fallback that scores query–chunk overlap.

    Computes a normalised lexical overlap score between a query and each
    candidate chunk, weighted by:
      - BM25 IDF of each matching term (terms rare across the corpus count
        more),
      - position boost (terms near the top of the chunk count slightly more —
        mirrors the 'lost in the middle' finding that relevant info at the
        edges is easier to use).

    This is the offline, deterministic counterpart to a neural CrossEncoder
    (e.g. BAAI/bge-reranker-base).  When a neural model is available it can
    be dropped in with the same interface: ``score(query, chunks) -> list[float]``.
    """

    def __init__(self, corpus_tokens: list[list[str]]):
        """corpus_tokens: one token-list per chunk in the corpus (for IDF)."""
        self._corpus_tokens = corpus_tokens
        self._idf: dict[str, float] = {}
        self._compute_idf()

    def _compute_idf(self) -> None:
        n = max(len(self._corpus_tokens), 1)
        df: Counter = Counter()
        for toks in self._corpus_tokens:
            for t in set(toks):
                df[t] += 1
        for t, c in df.items():
            # standard BM25-style smooth IDF
            self._idf[t] = math.log((n - c + 0.5) / (c + 0.5) + 1.0)

    def score(self, query: str, chunks: list[str]) -> list[float]:
        """Return a normalised relevance score per chunk (0..1, higher better)."""
        q_tok = _tokenize(query)
        if not q_tok:
            return [0.0] * len(chunks)
        q_counts = _token_set(q_tok)
        q_tf = {t: q_counts[t] for t in q_counts}

        scores: list[float] = []
        for chunk in chunks:
            c_tok = _tokenize(chunk)
            if not c_tok:
                scores.append(0.0)
                continue
            c_set = set(c_tok)
            if not c_set:
                scores.append(0.0)
                continue

            # overlap weight: sum of query-term idf for terms present in chunk,
            # multiplied by query tf (so multi-occurrence query terms count more).
            overlap = 0.0
            matched_terms: set[str] = set()
            for t, qtf in q_tf.items():
                if t in c_set:
                    overlap += self._idf.get(t, 0.0) * qtf
                    matched_terms.add(t)

            if overlap == 0.0:
                scores.append(0.0)
                continue

            # Position boost: term offsets near the start of the chunk get a
            # small multiplier.  Convert matched-terms to a first-occurrence
            # position map, then weight by 1 / (1 + normalised_offset).
            chunk_lower = chunk.lower()
            pos_sum = 0.0
            pos_count = 0
            clen = len(chunk_lower)
            for t in matched_terms:
                idx = chunk_lower.find(t)
                if idx >= 0:
                    pos = idx / max(clen, 1)  # 0..1
                    pos_sum += 1.0 / (1.0 + pos)
                    pos_count += 1
            pos_bonus = (pos_sum / max(pos_count, 1))  # ~0.5..1.0

            # Length normalisation: longer chunks dilute term density.
            length_norm = 1.0 / math.sqrt(1.0 + len(c_tok) / 200.0)

            score = overlap * pos_bonus * length_norm
            scores.append(score)
        # Normalise to 0..1 across the candidate set for stable display.
        mx = max(scores) if scores else 1.0
        if mx > 0:
            scores = [s / mx for s in scores]
        return scores


# ── Reciprocal Rank Fusion ─────────────────────────────────────────────────────

def _rrf_score(rank: int, k: int = 60) -> float:
    """Reciprocal Rank Fusion score for a single 항목 at a given 0-based rank."""
    return 1.0 / (k + rank + 1)


def rrf_fuse(
    dense_results: list[dict],
    bm25_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """Fuse two ranked result lists with Reciprocal Rank Fusion.

    Each input list must be pre-sorted by its own score descending.  Items are
    matched by ``chunk_id``; the fused score is the sum of RRF scores from each
    list.  Returns a new list sorted by fused score descending.
    """
    rrf: dict[str, float] = {}
    meta: dict[str, dict] = {}

    for rank, item in enumerate(dense_results):
        cid = item.get("chunk_id", "")
        rrf[cid] = rrf.get(cid, 0.0) + _rrf_score(rank, k)
        meta[cid] = item

    for rank, item in enumerate(bm25_results):
        cid = item.get("chunk_id", "")
        rrf[cid] = rrf.get(cid, 0.0) + _rrf_score(rank, k)
        # BM25 may surface chunks not in the dense top-k — keep their metadata
        if cid not in meta:
            meta[cid] = item

    fused = [(cid, rrf[cid]) for cid in rrf]
    fused.sort(key=lambda x: x[1], reverse=True)
    return [meta[cid] | {"fusion_score": score} for cid, score in fused]


# ── Hybrid retriever ───────────────────────────────────────────────────────────

class HybridRetriever:
    """Two-stage hybrid retrieval for the hamiGenZ pipeline.

    Stage 1 — hybrid candidate generation:
      - Dense: FAISS inner-product over the document's embedding index
        (existing behaviour, via VectorStore).
      - Sparse: BM25Okapi over the document's chunk token index.
      - Fuse with Reciprocal Rank Fusion (k=60).

    Stage 2 — lexical reranking:
      - Re-score the fused candidate set with LexicalReranker and take the
        top_k.  When a neural CrossEncoder is available, replace
        ``_rerank`` with a single model call.
    """

    def __init__(
        self,
        vector_store,       # backend.vector_store.VectorStore
        metadata_store,     # backend.document_processor.MetadataStore
        embedder,           # backend.vector_store.EmbeddingService
        vectors_dir: str,
        k_bm25: int = 15,
        k_dense: int = 15,
        k_final: int = 5,
        reranker: Optional[LexicalReranker] = None,
    ):
        self.vector_store = vector_store
        self.metadata_store = metadata_store
        self.embedder = embedder
        self.vectors_dir = Path(vectors_dir)
        self.k_bm25 = k_bm25
        self.k_dense = k_dense
        self.k_final = k_final
        self.reranker = reranker
        self._bm25: dict[str, BM25Okapi] = {}   # doc_id -> BM25 index
        self._bm25_tokens: dict[str, list[list[str]]] = {}  # doc_id -> per-chunk tokens
        self._corpus_tokens_all: list[list[str]] = []       # for global IDF in reranker

    # ── BM25 index management ────────────────────────────────────────────────

    def rebuild_all_bm25(self) -> dict[str, int]:
        """Rebuild every BM25 index from stored chunk metadata.

        Called on startup and after each document upload so the sparse index
        stays in sync without touching the original upload files.
        """
        rebuilt: dict[str, int] = {}
        self._bm25.clear()
        self._bm25_tokens.clear()
        self._corpus_tokens_all.clear()

        meta_dir = self.vectors_dir
        for meta_path in meta_dir.glob("*_meta.json"):
            doc_id = meta_path.stem.replace("_meta", "")
            try:
                import json
                with open(meta_path, encoding="utf-8") as f:
                    chunks = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            if not chunks:
                continue
            texts = [c.get("text", "") or "" for c in chunks]
            tokens = [_tokenize(t) for t in texts]
            self._bm25[doc_id] = BM25Okapi(tokens)
            self._bm25_tokens[doc_id] = tokens
            self._corpus_tokens_all.extend(tokens)
            rebuilt[doc_id] = len(tokens)

        # Rebuild the global lexical reranker from the full corpus.
        if self._corpus_tokens_all:
            self.reranker = LexicalReranker(self._corpus_tokens_all)
        else:
            self.reranker = None

        return rebuilt

    def _bm25_search(
        self, doc_id: str, query: str, top_k: int
    ) -> list[dict]:
        """Return BM25-ranked chunks for a single document."""
        index = self._bm25.get(doc_id)
        if index is None:
            return []
        tokens = self._bm25_tokens.get(doc_id, [])
        scores = index.get_scores(_tokenize(query))
        # Pair with metadata by position.
        meta_path = self.vectors_dir / f"{doc_id}_meta.json"
        try:
            import json
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
        except (json.JSONDecodeError, OSError):
            meta = []

        ranked: list[tuple[float, int]] = []
        for i, s in enumerate(scores):
            if i >= len(meta):
                break
            if s > 0:
                ranked.append((s, i))
        ranked.sort(key=lambda x: x[0], reverse=True)
        out: list[dict] = []
        for s, i in ranked[:top_k]:
            m = meta[i] if i < len(meta) else {}
            out.append({
                "chunk_id": m.get("chunk_id", f"{doc_id}_chunk_{i}"),
                "page_num": m.get("page_num"),
                "text": m.get("text", ""),
                "score": float(s),
                "filename": m.get("filename", ""),
                "source_type": m.get("source_type", "unknown"),
                "doc_id": doc_id,
            })
        return out

    # ── Public search API (mirrors VectorStore.search / search_all) ──────────

    def search(
        self,
        doc_id: Optional[str],
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """Hybrid search: dense + BM25 → RRF → rerank → top_k."""
        # --- Stage 1: candidate generation ---
        query_emb = self.embedder.embed_text(query)

        if doc_id:
            dense = self.vector_store.search(doc_id, query_emb, top_k=self.k_dense)
            bm25 = self._bm25_search(doc_id, query, top_k=self.k_bm25)
            fused = rrf_fuse(dense, bm25)
        else:
            dense = self.vector_store.search_all(query_emb, top_k=self.k_dense)
            # BM25 across all docs: collect per-doc, then merge.
            bm25_all: list[dict] = []
            for did in self._bm25:
                bm25_all.extend(self._bm25_search(did, query, top_k=self.k_bm25))
            # Dedupe by chunk_id, keep highest BM25 score.
            best: dict[str, dict] = {}
            for item in bm25_all:
                cid = item["chunk_id"]
                if cid not in best or item["score"] > best[cid]["score"]:
                    best[cid] = item
            bm25 = sorted(best.values(), key=lambda x: x["score"], reverse=True)
            fused = rrf_fuse(dense, bm25)

        # --- Stage 2: rerank ---
        if self.reranker is not None and fused:
            chunk_texts = [f.get("text", "") for f in fused]
            rerank_scores = self.reranker.score(query, chunk_texts)
            for item, rs in zip(fused, rerank_scores):
                item["rerank_score"] = rs
            fused.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)

        return fused[:top_k]

    def doc_count(self) -> int:
        return len(self._bm25)
