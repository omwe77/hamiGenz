# hamiGenZ

**Tagline:** "Don't understand it? Ask hamiGenZ."

Nepal's AI document understanding platform — fully local, free, offline-capable.

## What's New (Technology Enhancements)

### OKF Knowledge Layer (Open Knowledge Format)

** replaces the old hybrid RAG retriever ** — instead of chunking documents into
vector-searchable fragments and losing structure, hamiGenZ now uses a curated
knowledge layer based on the Open Knowledge Format (OKF) spec (Google Cloud, June 2026).

OKF treats knowledge as durable, readable facts — not as a haystack to search.
For Nepal documents this matters: a passport's page-1 data and page-N disclaimer
are one document, but RAG slices them into disconnected chunks. OKF keeps them

- **Markdown concept files** — one file per knowledge concept (document type,
  form guide, OCR rule, field definition), with YAML frontmatter
- **Explicit cross-links** — concepts link to each other with `[[concept-id]]`,
  forming a traversable knowledge graph instead of a bag of chunks
- **Git-native** — version-controlled, diffable, reviewable in PRs
- **Deterministic lookup** — type/tag/keyword search, not cosine-similarity lottery
- **Provenance** — each concept has `verified`, `status`, `owner`, `resource` fields
- **Devanagari-first** — tags and body content in Nepali script, not just English

**Routing:** user queries are classified into three buckets:
- `okf` — curated knowledge question (e.g. "passport के हो", "कसरी भर्ने") → OKF bundle
- `document` — question about a specific uploaded document → vector search
- `general` — Nepal info / chit-chat → official_answer service or LLM

**Concept types in hamiGenZ's OKF bundle:**
- `DocumentType` — Nepal passport, citizenship certificate, NID card, voter ID
- `FormGuide` — official form-filling guidelines
- `OCRRule` — post-processing rules for Tesseract/EasyOCR/TrOCR output
- `FieldDefinition` — what each field on Nepal documents means

**Knowledge files:** `data/okf/` — 7 concept files, 4 types, cross-linked,
with Devanagari + English tags, all verified, owned by hamiGenZ curated knowledge.

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
- **EasyOCR** (`ne` model) — secondary OCR engine with native Devanagari support, used alongside Tesseract for comparison
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
│   ├── okf_bundle.py          # NEW: Open Knowledge Format bundle loader + router
│   ├── ocr_engines.py         # NEW: EasyOCR + TrOCR extended OCR engines
│   ├── feedback_store.py      # user ratings SQLite store
│   ├── action_extractor.py    # Requirements/deadlines/fees extraction
│   ├── form_understanding.py  # Form field detection + explanation
│   ├── official_answer.py     # Curated official-source answering
│   └── source_registry.py     # Curated authoritative Nepali sources
├── data/
│   ├── okf/          # NEW: OKF knowledge bundle (markdown concept files)
│   │   ├── index.md
│   │   ├── document-types/   # Nepal document type definitions
│   │   ├── forms/            # Form-filling guidelines
│   │   ├── ocr/              # OCR post-processing rules
│   │   └── fields/           # Field meaning reference
│   ├── uploads/      # Uploaded documents
│   ├── vectors/      # FAISS vector indexes
│   ├── knowledge/    # Official source knowledge cache
│   ├── feedback.db   # User feedback SQLite
│   └── hamigenz.db   # Document metadata + chunk registry
├── frontend/         # Next.js + React
│   └── src/
│       ├── components/workspace/   # Explain/document UI
│       └── lib/hamigenz-api.ts    # API client
├── tests/            # Test suite
└── docs/             # Architecture, evaluation, security docs
```

## Phase 1 MVP Features

- File upload (PDF, PNG, JPG, TIFF)
- PDF text extraction (pdfplumber + PyMuPDF)
- OCR for scanned documents (Tesseract, Nepali + English)
- Extended OCR engines: EasyOCR + TrOCR for Devanagari and handwriting
- **OKF Knowledge Layer** — curated Nepal document knowledge (Open Knowledge Format),
  replacing chunking-based hybrid RAG retriever
- **User feedback loop (thumbs up/down)** — SQLite-backed, best-effort submission
- Sentence-level chunking with overlap
- Local embeddings (sentence-transformers paraphrase-multilingual-MiniLM-L12-v2)
- FAISS vector storage per document (for user-uploaded document search)
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
- **Knowledge layer:** OKF (Open Knowledge Format) — markdown + YAML, git-native
- **Document search:** FAISS (dense) for uploaded user documents
- **OCR:** pytesseract + Tesseract OCR (nepali traineddata) + EasyOCR + TrOCR
- **PDF:** pdfplumber + PyMuPDF (fitz)
- **Frontend:** Next.js + React
- **DB:** SQLite (metadata + feedback), FAISS (vectors)

## Running

```bash
# Activate venv
.\\.venv\\Scripts\\Activate.ps1   # PowerShell
# or
.venv\\Scripts\\activate.bat      # CMD

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
| POST | /ask | Ask question — routes to OKF knowledge, document search, or general |
| POST | /explain | Explain text in simple language |
| POST | /actions | Extract requirements, deadlines, fees |
| POST | /forms/detect | Detect form fields in text |
| POST | /forms/explain-field | Explain one form field |
| POST | /ask-general | Ask Nepal-info question without document |
| GET | /knowledge/sources | List curated official sources |
| GET | /knowledge/classify | Classify a URL against registry |
| **POST** | **/feedback** | **Record thumbs up/down rating** |
| **GET** | **/feedback/stats** | **Aggregate feedback stats** |
| GET | /documents | List uploaded documents |
| DELETE | /documents/{doc_id} | Delete a document |
| GET | /documents/{doc_id}/viewer | Per-page text viewer |
| GET | /documents/{doc_id}/search-text | Search document text |
| GET | /endpoints | Live HTML API reference |

## OKF Knowledge Bundle

The OKF bundle lives in `data/okf/` and is loaded at startup. You can extend it
by adding new `.md` concept files — no code changes needed.

**Adding a new document type:**
1. Create `data/okf/document-types/<name>.md`
2. Add YAML frontmatter with `type: DocumentType` and tags
3. Write the body in markdown with page-by-page structure
4. Restart the backend — the bundle auto-loads

**OKF spec reference:** https://cloud.google.com/open-knowledge-format

## Accuracy Priority

Accuracy > Grounding > Usefulness > Simplicity > Visual polish

Prefer: "I could not verify this from an authoritative source."
Over: confident but unsupported answer.

## Development Phases

1. **Phase 1 — MVP:** Core document understanding pipeline, local/free, publicly usable ✅
2. **Phase 2 — Official Nepal Knowledge:** Curated KB (passport, NID, traffic, govt services) ✅
3. **Phase 3 — Action Features:** Checklists, deadline/fee extraction, form filling ✅
4. **Phase 4 — Strong Verification:** Contradiction detection, confidence scoring ✅
5. **Phase 5 — Expansion:** PWA, camera scanning, voice, API, multi-language
6. **Phase 6 — Tech Enhancement:** OKF knowledge layer, user feedback, extended OCR ✅ (current)

## License

MIT — built for Nepal, open for everyone.
