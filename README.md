# hamiGenZ

**Tagline:** "Don't understand it? Ask hamiGenZ."

Nepal's AI document understanding platform — fully local, free, offline-capable.

---

## OKF Knowledge Layer — Current State

hamiGenZ uses the Open Knowledge Format (OKF) v0.2 (Google Cloud, June 2026) as its
curated knowledge layer for Nepal document understanding. This replaces the old hybrid
RAG retriever. OKF keeps knowledge as durable, structured Markdown files with YAML
frontmatter — not as chunks lost in a vector index.

**Architecture:**

```
USER
↓
QUERY ROUTER
├── curated/static knowledge → OKF bundle (data/okf/)
├── user's uploaded document → FAISS vector search
├── current official information → official_answer service
└── mixed query → controlled multi-source retrieval

retrieved evidence
↓
LLM answer generation
↓
grounding validation
↓
contradiction verification
↓
confidence/provenance
↓
final answer + citations
```

**What exists today:**

| File | Status | Notes |
|------|--------|-------|
| `backend/okf_bundle.py` | ✅ Complete | OKF v0.2 loader, search, graph traversal, router |
| `backend/okf_validator.py` | ✅ Complete | Validates OKF conformance: YAML, type, status, verified, links, duplicates |
| `data/okf/index.md` | ✅ Complete | Bundle index with proper v0.2 frontmatter |
| `data/okf/document-types/passport.md` | ✅ Complete | Nepal Ordinary Passport — page-by-page, standard Markdown links, v0.2 metadata |
| `data/okf/document-types/citizenship.md` | ✅ Complete | Nepal Citizenship Certificate — fixed corrupted text, v0.2 metadata |
| `data/okf/document-types/national_id.md` | ✅ Complete | Nepal NID/Citizen ID — fixed Korean/Bengali corruption, v0.2 metadata |
| `data/okf/document-types/voter_id.md` | ✅ Complete | Nepal Voter ID — fixed text corruption, v0.2 metadata |
| `data/okf/forms/fill-guidelines.md` | ✅ Complete | Form-filling guidelines, v0.2 metadata |
| `data/okf/ocr/post-processing.md` | ✅ Complete | OCR post-processing rules (10 rules), v0.2 metadata |
| `data/okf/fields/field-meanings.md` | ✅ Complete | Field reference — fixed Japanese corruption, v0.2 metadata |
| `backend/main.py` /ask routing | ⚠️ Partial | OKF routing works; body[:1500] truncation still present; page_num=0 for OKF citations |
| `backend/main.py` /ask-general | ⚠️ Needs work | Official-answer integration incomplete; general query dead path |
| `backend/okf_bundle.py` link parsing | ⚠️ Needs work | Still uses [[...]] custom syntax regex; needs standard Markdown link parsing |
| Golden query tests | ❌ Not started | Need realistic query set with routing + grounding evaluation |
| OKF audit against gov't sources | ❌ Not started | Claims not yet verified against Nepal government authorities |

---

## Goals

### Accuracy Priority
Accuracy > Grounding > Usefulness > Simplicity > Visual polish

Prefer: "I could not verify this from an authoritative source."
Over: confident but unsupported answer.

### OKF Conformance (Phase 1 — In Progress)
- [x] OKF v0.2 spec reviewed from GoogleCloudPlatform/knowledge-catalog
- [x] Markdown concept files with YAML frontmatter
- [x] `type` required, non-empty
- [x] `status` uses valid values: draft | stable | deprecated
- [x] `verified` is a list of {by, at} objects, not a boolean
- [x] `generated` field present on all concepts
- [x] `sources` field present on verified concepts
- [x] Custom `[[...]]` syntax replaced with standard Markdown links in data files
- [x] OKF validator (`backend/okf_validator.py`) catches conformance issues
- [ ] Standard Markdown link parsing in okf_bundle.py (still uses [[...]] regex)
- [ ] `okf_version: "0.2"` declared in index.md frontmatter

### Data Quality (Phase 1 — In Progress)
- [x] Corrupted text fixed in passport.md (द_last → उपनाम)
- [x] Corrupted text fixed in citizenship.md (नेपाल गण-thousand → नेपाल गणराज्य; removed hallucinated citizenship categories)
- [x] Corrupted text fixed in national_id.md (Korean "धर्म근혜 나라" → नेपाल header; Bengali title removed; रगत कunarो → रगत समूह)
- [x] Corrupted text fixed in voter_id.md (সrichmentको → सपत्नीको)
- [x] Corrupted text fixed in field-meanings.md (Japanese katakana "सにとってको" → सपत्नीको)
- [ ] Every factual claim audited against Nepal government authoritative sources
- [ ] Unsupported claims removed or marked unverified

### Routing (Phase 1 — Partially Done)
- [x] Three-bucket classification: okf / document / general
- [x] Doc_id precedence for uploaded-document queries
- [x] Devanagari + English + Romanized Nepali handling
- [x] Alias support (passport/राहदानी, citizenship/नागरिकता, etc.)
- [ ] Intent + entity detection instead of pure keyword matching
- [ ] False-positive routing tests (e.g. "passport" in uploaded doc query shouldn't trigger OKF only)
- [ ] General query path actually uses official_answer service (currently dead)

### Context Preservation (Phase 1 — Broken, Needs Fix)
- [ ] REMOVE `body[:1500]` truncation in main.py (destroys the exact advantage of OKF)
- [ ] Section-aware context selection when limits require reduction
- [ ] Preserve trailing warnings/disclaimers/exceptions
- [ ] Regression test: answer depends on information near END of a concept

### Provenance & Citations (Phase 1 — Partially Done)
- [x] OKF evidence distinct from document-page evidence in code
- [ ] REMOVE `page_num: 0` for OKF citations (semantically wrong)
- [ ] OKF citations show: source_type="okf", concept_id, concept_path, concept_title
- [ ] Document citations show: source_type="document", doc_id, page_num, chunk
- [ ] Official-source citations show: source_type="official", source_url, retrieved_at

### Trust, Verification, Freshness (Phase 1 — Not Started)
- [ ] `stale_after` field used to flag potentially outdated knowledge
- [ ] Current gov't queries prefer official_answer over static OKF
- [ ] Staleness surfaced in answers, not silently presented as current

### Graph Behavior (Phase 1 — Partially Done)
- [x] Outgoing links extracted from Markdown bodies
- [ ] Standard Markdown link parsing (not [[...]] regex)
- [ ] Reverse/backlinks where useful
- [ ] One-hop related concepts
- [ ] Controlled two-hop traversal with cycle detection
- [ ] Progressive disclosure: index → concept → linked → evidence

### Search Quality (Phase 1 — Partially Done)
- [x] Type match, tag match, keyword overlap
- [x] Devanagari-aware tokenization
- [x] Multi-word phrase matching
- [ ] Exact concept ID lookup
- [ ] Section relevance scoring
- [ ] Provenance/trust filtering
- [ ] Freshness filtering

### Testing (Phase 1 — Not Started)
- [ ] OKF parsing tests (valid/invalid frontmatter, missing type, unknown metadata)
- [ ] Graph tests (links, backlinks, cycles, deduplication)
- [ ] Search tests (English, Nepali, Romanized, aliases, trailing-section retrieval)
- [ ] Routing tests (OKF/document/official/mixed/ambiguous)
- [ ] Provenance tests (no page 0 for OKF)
- [ ] Freshness tests (current vs stale)
- [ ] Safety tests (prompt injection, malicious text, oversized inputs, path traversal)
- [ ] Regression test (trailing content must be retrieved)
- [ ] Golden query set with routing + grounding evaluation

### Documentation (Phase 1 — In Progress)
- [x] README.md describes OKF architecture
- [x] README.md lists all concept files and types
- [ ] README.md accurately describes routing (not "OKF replaces RAG")
- [ ] README.md documents how to add a concept
- [ ] README.md documents provenance and verification
- [ ] README.md documents limitations

---

## Phase 1 MVP Features

- File upload (PDF, PNG, JPG, TIFF)
- PDF text extraction (pdfplumber + PyMuPDF)
- OCR for scanned documents (Tesseract, Nepali + English)
- Extended OCR engines: EasyOCR + TrOCR for Devanagari and handwriting
- **OKF Knowledge Layer** — curated Nepal document knowledge (Open Knowledge Format),
  replacing chunking-based hybrid RAG retriever
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
- **Knowledge layer:** OKF (Open Knowledge Format) — Markdown + YAML, git-native
- **Document search:** FAISS (dense) for uploaded user documents
- **OCR:** pytesseract + Tesseract OCR (nepali traineddata) + EasyOCR + TrOCR
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
| POST | /feedback | Record thumbs up/down rating |
| GET | /feedback/stats | Aggregate feedback stats |
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
4. Use standard Markdown links: `[text](../path/to/concept.md)`
5. Run `python -m backend.okf_validator` to check conformance
6. Restart the backend — the bundle auto-loads

**Validating the bundle:**
```bash
python -m backend.okf_validator
```

**OKF spec reference:** https://cloud.google.com/open-knowledge-format

## Project Structure

```
hamigenz/
├── backend/          # Python + FastAPI backend
│   ├── main.py        # FastAPI app, all endpoints
│   ├── document_processor.py  # PDF/image extraction, chunking
│   ├── vector_store.py        # FAISS + sentence-transformers
│   ├── llm_service.py         # Ollama + grounding + verification
│   ├── okf_bundle.py          # OKF bundle loader + router
│   ├── okf_validator.py       # OKF conformance validator
│   ├── ocr_engines.py         # EasyOCR + TrOCR extended OCR engines
│   ├── feedback_store.py      # user ratings SQLite store
│   ├── action_extractor.py    # Requirements/deadlines/fees extraction
│   ├── form_understanding.py  # Form field detection + explanation
│   ├── official_answer.py     # Curated official-source answering
│   └── source_registry.py     # Curated authoritative Nepali sources
├── data/
│   ├── okf/          # OKF knowledge bundle (markdown concept files)
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

## License

MIT — built for Nepal, open for everyone.

## Connect

- **GitHub:** https://github.com/omwe77/hamiGenZ
- **Developer:** Om (omwe77) — London Metropolitan University
- **Mailing list / feedback:** Open a GitHub issue
