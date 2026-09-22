# hamiGenZ

**Tagline:** "Don't understand it? Ask hamiGenZ."

Nepal's AI document understanding platform — fully local, free, offline-capable.

## What's New (Technology Enhancements)

### Hybrid Retrieval (BM25 + Dense + RRF Fusion)
Traditional RAG uses only vector embeddings for search, which fails on exact keywords, serial numbers, legal terms, and domain-specific vocabulary. We now use **hybrid retrieval**:
- **Dense vector search** (FAISS + sentence-transformers) for semantic meaning
- **BM25 keyword search** for exact term matching (Nepali legal terms, passport numbers, fees)
- **Reciprocal Rank Fusion (RRF)** to combine both scores — proven 26-31% precision improvement in 2025-2026 benchmarks
- **Two-stage reranking** with lexical overlap scorer (position-aware, IDF-weighted, length-normalized) — plug-compatible with neural cross-encoders like BAAI/bge-reranker-base

*Reference: "From BM25 to Corrective RAG" (arXiv 2604.01733), "Hybrid RAG" benchmarks (2025-2026), DeNA LLM Study Part 4 (2025)*

### User Feedback Loop
Thumbs up/down buttons on every explanation, stored in SQLite. This closes the loop:
- Real user satisfaction signal (cheapest meaningful quality metric per DeepLearning.AI RAG evaluation guide)
- Running aggregate stats (helpful vs. not helpful counts, up-rate %)
- Foundation for future active learning / fine-tuning data collection

*Reference: ADT-RAG feedback mechanism, PatchRAG (arXiv 2604.06647) — feedback adaptation as a measurable RAG dimension*

### Contextual Chunking
Each stored chunk carries its document-level context, improving retrieval relevance by preserving document identity through the embedding space.

*Reference: Anthropic contextual retrieval pattern, "Vision-Guided Chunking" (arXiv 2506.16035), ACL 2026 "Adaptive Chunking" paper*

### Modern Nepali OCR Path
Documented alternative to Tesseract for Devanagari:
- **PaddleOCR devanagari_PP-v5** — purpose-built for printed Devanagari, runs on CPU, no fine-tuning needed
- **TrOCR fine-tuned for Nepali (paudelanil/trocr-devanagari-2)** — for handwritten field values
- Four-stage pipeline: detection → PaddleOCR (printed labels) + TrOCR (handwritten values) → SpaCy NER → form fill

*Reference: Sandip Acharya "Why Nepali OCR is Brutally Hard" (Medium 2026), paudelanil/trocr-devanagari-2 on HuggingFace, nepOCR project*

### Multimodal RAG Ready
Architecture supports future vision-guided chunking with LMMs for multi-page tables, embedded figures, and cross-page context — the 2025 direction beyond text-only chunking.

## Project Structure

```
hamigenz/
├── backend/          # Python + FastAPI backend
│   ├── main.py        # FastAPI app, all endpoints
│   ├── document_processor.py  # PDF/image extraction, chunking
│   ├── vector_store.py        # FAISS + sentence-transformers
│   ├── llm_service.py         # Ollama + grounding + verification
│   ├── hybrid_retriever.py    # NEW: BM25 + dense + RRF + rerank
│   ├── feedback_store.py      # NEW: user ratings SQLite store
│   ├── action_extractor.py    # Requirements/deadlines/fees extraction
│   ├── form_understanding.py  # Form field detection + explanation
│   ├── official_answer.py     # Curated official-source answering
│   └── source_registry.py     # Curated authoritative Nepali sources
├── frontend/         # Next.js + React
│   └── src/
│       ├── components/workspace/   # Explain/document UI
│       └── lib/hamigenz-api.ts    # API client
├── data/             # Uploads, vectors, knowledge base, feedback.db
├── tests/            # Test suite
└── docs/             # Architecture, evaluation, security docs
```

## Phase 1 MVP Features

- File upload (PDF, PNG, JPG, TIFF)
- PDF text extraction (pdfplumber + PyMuPDF)
- OCR for scanned documents (Tesseract, Nepali + English)
- **NEW: Hybrid retrieval (BM25 + dense + RRF fusion + lexical reranking)**
- **NEW: User feedback loop (thumbs up/down)**
- Sentence-level chunking with overlap
- Local embeddings (sentence-transformers paraphrase-multilingual-MiniLM-L12-v2)
- FAISS vector storage per document
- Ollama LLM (qwen3:8b)
- Grounding validation (claim extraction vs evidence)
- Verification layer (contradiction detection, confidence scoring 0-100)
- Explanation engine (original / simple / very_simple levels)
- Language detection (Nepali, English, Romanized Nepali, mixed)
- Form-filling explanation mode with SAMPLE markers
- Official-source answering from curated registry
- Action extraction (checklists, deadlines, fees, next steps)
- Fully local and free — no paid APIs
- Security hardening (magic-byte validation, path containment, rate limiting, prompt injection defense, CORS allowlist)

## Tech Stack

- **Backend:** Python 3.11 + FastAPI + Uvicorn
- **LLM:** Ollama + qwen3:8b (local)
- **Embeddings:** sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)
- **Hybrid retrieval:** FAISS (dense) + rank-bm25 (sparse) + RRF fusion + lexical reranker
- **Vector DB:** FAISS (local, no server needed)
- **OCR:** pytesseract + Tesseract OCR (nepali traineddata)
- **PDF:** pdfplumber + PyMuPDF (fitz)
- **Frontend:** Next.js + React
- **DB:** SQLite (metadata + feedback), FAISS (vectors)

## Running

```bash
# Activate venv
.\.venv\Scripts\Activate.ps1   # PowerShell
# or
.venv\Scripts\activate.bat      # CMD

# Start backend (Ollama must be running with qwen3:8b loaded)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Start frontend (separate terminal)
cd frontend
npm run dev
```

Or use the provided scripts:
```bash
./run.sh    # Windows: start backend + frontend together
./setup-github.sh   # Initial GitHub remote setup
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health + model info |
| POST | /upload | Upload document (PDF/image) for analysis |
| POST | /ask | Ask question about documents |
| POST | /explain | Explain text in simple language |
| POST | /actions | Extract requirements, deadlines, fees |
| POST | /forms/detect | Detect form fields in text |
| POST | /forms/explain-field | Explain one form field |
| POST | /ask-general | Ask Nepal-info question without document |
| GET | /knowledge/sources | List curated official sources |
| GET | /knowledge/classify | Classify a URL against registry |
| **POST** | **/feedback** | **NEW: Record thumbs up/down rating** |
| **GET** | **/feedback/stats** | **NEW: Aggregate feedback stats** |
| GET | /documents | List uploaded documents |
| DELETE | /documents/{doc_id} | Delete a document |
| GET | /documents/{doc_id}/viewer | Per-page text viewer |
| GET | /documents/{doc_id}/search-text | Search document text |
| GET | /endpoints | Live HTML API reference |

## Accuracy Priority

Accuracy > Grounding > Usefulness > Simplicity > Visual polish

Prefer: "I could not verify this from an authoritative source."
Over: confident but unsupported answer.

## Development Phases

1. **Phase 1 — MVP:** Core document RAG pipeline, local/free, publicly usable ✅
2. **Phase 2 — Official Nepal Knowledge:** Curated KB (passport, NID, traffic, govt services) ✅
3. **Phase 3 — Action Features:** Checklists, deadline/fee extraction, form filling ✅
4. **Phase 4 — Strong Verification:** Contradiction detection, confidence scoring ✅
5. **Phase 5 — Expansion:** PWA, camera scanning, voice, API, multi-language
6. **Phase 6 — Tech Enhancement:** Hybrid retrieval, user feedback, modern OCR path ✅ (current)

## License

MIT — built for Nepal, open for everyone.
