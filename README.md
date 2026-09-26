# hamiGenZ

**Tagline:** "Don't understand it? Ask hamiGenZ."

Nepal's AI document understanding platform — fully local, free, offline-capable.

---

## OKF Knowledge Layer — Current State

hamiGenZ uses the Open Knowledge Format (OKF) v0.2 (Google Cloud, July 2026) as its
curated knowledge layer for Nepal document understanding. OKF keeps knowledge as durable,
structured Markdown files with YAML frontmatter — not as chunks lost in a vector index.

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
| `backend/okf_bundle.py` | ✅ Complete | OKF v0.2 loader, search (full-body section scoring), graph traversal, deterministic router |
| `backend/okf_validator.py` | ✅ Complete | Validates OKF conformance: YAML, type, status, verified, sources, links, duplicates |
| `data/okf/index.md` | ✅ Complete | Bundle index with `okf_version: "0.2"` frontmatter |
| `data/okf/document-types/passport.md` | ✅ Complete | Nepal Ordinary Passport — 34/66 pages, standard Markdown links, v0.2 metadata |
| `data/okf/document-types/citizenship.md` | ✅ Complete | Nepal Citizenship Certificate — fixed corrupted text, v0.2 metadata |
| `data/okf/document-types/national_id.md` | ✅ Complete | Nepal NID/Citizen ID — fixed corruption, v0.2 metadata |
| `data/okf/document-types/voter_id.md` | ✅ Complete | Nepal Voter ID — fixed text corruption, v0.2 metadata |
| `data/okf/forms/fill-guidelines.md` | ✅ Complete | Form-filling guidelines, v0.2 metadata |
| `data/okf/ocr/post-processing.md` | ✅ Complete | OCR post-processing rules (10 rules), v0.2 metadata |
| `data/okf/fields/field-meanings.md` | ✅ Complete | Field reference — fixed corruption, v0.2 metadata |
| `backend/main.py` /ask routing | ✅ Complete | OKF routing, section-aware context, no blind truncation, page_num=None for OKF |
| `backend/main.py` /ask-general | ✅ Complete | Routes structural knowledge to OKF, current info to official_answer |
| `backend/okf_bundle.py` link parsing | ✅ Complete | Standard Markdown link parsing, not [[...]] custom syntax |
| Golden query tests | ✅ Complete | 79 tests covering parsing, graph, search, routing, corruption, injection, citations |

---

## Goals

### Accuracy Priority
Accuracy > Grounding > Usefulness > Simplicity > Visual polish

Prefer: "I could not verify this from an authoritative source."
Over: confident but unsupported answer.

### OKF Conformance (Complete)
- [x] OKF v0.2 spec reviewed from GoogleCloudPlatform/knowledge-catalog
- [x] Markdown concept files with YAML frontmatter
- [x] `type` required, non-empty — any valid string accepted (spaces, Unicode)
- [x] `status` uses valid values: draft | stable | deprecated
- [x] `verified` is a list of {by, at} objects, not a boolean
- [x] `generated` field present on all concepts
- [x] `sources` field present on concepts with provenance
- [x] Standard Markdown links in data files AND in okf_bundle.py parser
- [x] OKF validator (`backend/okf_validator.py`) catches conformance issues
- [x] `okf_version: "0.2"` declared in index.md frontmatter
- [x] Unknown type values tolerated (§11)
- [x] Broken links tolerated (§11)
- [x] Unknown frontmatter fields preserved
- [x] Nested index.md/log.md handled at every directory level

### Data Quality (Complete)
- [x] All corrupted text fixed across all concept files
- [x] Nepal passport page count corrected to 34/66 pages (authoritative: Department of Passports)
- [x] `जप्म` → `जन्म` (correct Devanagari for 'birth')
- [x] `रगत कunarो` → `रगत समूह` (blood group)
- [x] `ठiegाना` → `ठेगाना` (address)
- [x] Every concept has `sources` with resource URL
- [x] Trust tier is machine-confirmed (process/hamigenz-okf-curator), not human-reviewed

### Routing (Complete)
- [x] Four-bucket classification: okf / document / official / general
- [x] Doc_id precedence for uploaded-document queries
- [x] Devanagari + English + Romanized Nepali handling
- [x] Alias support (passport/राहदानी, citizenship/नागरिकता, etc.)
- [x] Current-info keywords route to official_answer (fees, deadlines, procedures)
- [x] Structural knowledge routes to OKF (document types, fields, forms)
- [x] "What is the passport fee?" → official, not OKF
- [x] "What does my document say?" → document search
- [x] "What is a Nepal passport?" → OKF

### Context Preservation (Complete)
- [x] No `body[:1500]` truncation in main.py
- [x] Section-aware context selection when limits require reduction
- [x] Trailing warnings/disclaimers/exceptions preserved when relevant
- [x] Regression test: answer depends on information near END of a concept
- [x] Head+tail section truncation preserves important content at both ends

### Provenance & Citations (Complete)
- [x] OKF evidence distinct from document-page evidence in code
- [x] `page_num=None` for OKF citations (not 0 — OKF is not page-based)
- [x] OKF citations show: source_type="okf", concept_id, concept_title, trust_tier
- [x] Document citations show: source_type="document", page_num, chunk
- [x] Official-source evidence carries source identity

### Trust, Verification, Freshness (Complete)
- [x] `stale_after` field parsed and used to flag potentially outdated knowledge
- [x] `trust_tier` derived from verified: unverified | machine-confirmed | human-reviewed
- [x] Current gov't queries prefer official_answer over static OKF
- [x] Staleness computable via is_stale property

### Graph Behavior (Complete)
- [x] Standard Markdown link parsing (not [[...]] regex)
- [x] Outgoing links extracted from Markdown bodies
- [x] Reverse/backlinks where useful
- [x] One-hop related concepts
- [x] Controlled two-hop traversal with cycle detection
- [x] Progressive disclosure: index → concept → linked → evidence

### Search Quality (Complete)
- [x] Type match, tag match, keyword overlap
- [x] Devanagari-aware tokenization
- [x] Multi-word phrase matching
- [x] Full-body section scanning (not first-N-chars only)
- [x] Exact concept ID lookup
- [x] Section relevance scoring across ALL sections
- [x] Efficient ranking: search() computed once in get_context_for_llm

### Testing (Complete — 273 tests passing)
- [x] OKF parsing tests (valid/invalid frontmatter, missing type, unknown metadata)
- [x] Graph tests (links, backlinks, cycles, deduplication)
- [x] Search tests (English, Nepali, trailing-section retrieval)
- [x] Routing tests (OKF/document/official/mixed/ambiguous)
- [x] Provenance tests (no page 0 for OKF)
- [x] Freshness tests (stale_after parsing)
- [x] Safety tests (prompt injection in OKF content)
- [x] Regression test (trailing content must be retrieved)
- [x] Pipeline tests (embedder, chunker, Ollama connectivity)
- [x] Prompt guard tests (injection neutralization)
- [x] Security tests (path traversal, filename sanitization)
- [x] Source registry tests (domain lookup, freshness, classification)

### Documentation (Complete)
- [x] README.md describes OKF architecture accurately
- [x] README.md lists all concept files and types
- [x] README.md accurately describes routing (OKF ≠ all retrieval)
- [x] README.md documents how to add a concept
- [x] README.md documents provenance and verification
- [x] README.md documents limitations

---

## Phase 1 MVP Features

- File upload (PDF, PNG, JPG, TIFF)
- PDF text extraction (pdfplumber + PyMuPDF)
- OCR for scanned documents (Tesseract, Nepali + English)
- Extended OCR engines: EasyOCR + TrOCR for Devanagari and handwriting
- **OKF Knowledge Layer** — curated Nepal document knowledge (Open Knowledge Format v0.2),
  for structured knowledge about document types, fields, forms, and OCR rules
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
- User feedback loop (thumbs up/down)
- Fully local and free — no paid APIs
- Security hardening (magic-byte validation, path containment, rate limiting, prompt injection defense, CORS allowlist)

## Tech Stack

- **Backend:** Python 3.11 + FastAPI + Uvicorn
- **LLM:** Ollama + qwen3:8b (local)
- **Embeddings:** sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)
- **Knowledge layer:** OKF (Open Knowledge Format) v0.2 — Markdown + YAML, git-native
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
4. Use standard Markdown links: `[text](../path/to/concept.md)` — NOT `[[...]]`
5. Run `python -m backend.okf_validator` to check conformance
6. Restart the backend — the bundle auto-loads

**Validating the bundle:**
```bash
.venv\\Scripts\\python -m backend.okf_validator
```

**Trust tiers:**
- `unverified` — no `verified` field
- `machine-confirmed` — verified by process: or agent: actors only
- `human-reviewed` — verified by a human: actor

hamiGenZ's OKF concepts are **machine-confirmed** (curated by `process/hamigenz-okf-curator/v0.1`).
They are NOT human-reviewed. See the OKF spec §5.3 for trust tier derivation.

**OKF spec reference:** https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md

## Limitations

- OKF concepts are machine-confirmed, not human-reviewed — verify critical facts
  against authoritative sources before relying on them for legal/official purposes.
- Static OKF knowledge may become stale — `stale_after` dates flag when re-verification
  is needed. Current fees, deadlines, and procedures should be verified via the
  official-answer service.
- The knowledge bundle covers Nepal passport, citizenship, NID, voter ID, form-filling,
  and OCR rules. It does not cover every Nepal document type or government process.
- Retrieval is keyword + type/tag overlap based, not semantic vector search. For
  curated knowledge this is deterministic and cheap; for uploaded documents, FAISS
  vector search is used instead.

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
│   └── tests/            # Test suite (273 tests passing)
└── docs/             # Architecture, evaluation, security docs
```

## License

MIT — built for Nepal, open for everyone.

## Connect

- **GitHub:** https://github.com/omwe77/hamiGenZ
- **Developer:** Om (omwe77) — London Metropolitan University
- **Mailing list / feedback:** Open a GitHub issue
