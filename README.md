# hamiGenZ — Nepal-Focused AI Document Understanding & Grounded Knowledge Platform

> A local-first, privacy-centric AI platform engineered to make complex Nepali administrative notices, government forms, and civil documents universally understandable. Built on the **Open Knowledge Format (OKF v0.2)**, offline multilingual embeddings, Devanagari OCR, and a strict verification layer—guaranteeing verifiable provenance and zero hallucinations.

[![Tests](https://img.shields.io/badge/Tests-282%20Passed-2ecc71?style=for-the-badge)](https://github.com/omwe77/hamiGenz/tree/main/tests)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.3-black?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![LLM](https://img.shields.io/badge/LLM-Ollama%20(qwen3%3A8b)-orange?style=for-the-badge)](https://ollama.ai)
[![Embeddings](https://img.shields.io/badge/Embeddings-paraphrase--multilingual-blue?style=for-the-badge)](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)

---

## 1. Problem & Context: Why hamiGenZ Matters in Nepal

Navigating public services in Nepal presents severe cognitive and linguistic hurdles:
- **Administrative Complexity:** Official guidelines for vital documents (Citizenship Certificates, e-Passports, National Identity Cards (NID), and Voter IDs) are published across disparate government gazettes, complex legal PDFs, and scanned circulars.
- **Linguistic Hurdles:** Notices frequently mix formal bureaucratic Devanagari, English, and colloquial Romanized Nepali.
- **The Pitfall of General-Purpose LLMs:** Standard cloud LLMs hallucinate obsolete fee structures, fabricate nonexistent embassy procedures, and cannot reliably parse degraded Devanagari scans.
- **Privacy Constraints:** Citizens should never be forced to upload sensitive identity records to third-party cloud AI vendors.

**hamiGenZ** addresses this gap as a **fully local, grounded document-understanding platform**. It ingests citizen documents, extracts bilingual text via specialized OCR, routes queries against an authoritative structured knowledge layer, and produces plain-language explanations backed by verifiable citations.

---

## 2. Key Concepts & The Knowledge Layer: OKF Beyond Conventional RAG

A core architectural pillar of hamiGenZ is moving beyond standard naive Retrieval-Augmented Generation (RAG):

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Why OKF is Not Just RAG                         │
├───────────────────────────────────┬────────────────────────────────────┤
│ Standard Chunk-Based RAG          │ Open Knowledge Format (OKF v0.2)   │
├───────────────────────────────────┼────────────────────────────────────┤
│ Statistical chunk similarity      │ Canonical, curated concept graphs  │
│ Context lost across split chunks  │ Durable frontmatter & provenance   │
│ Blind retrieval of outdated info  │ Versioned trust tiers & validation │
│ No relationship awareness         │ Bounded graph link traversal       │
└───────────────────────────────────┴────────────────────────────────────┘
```

### The Role of Open Knowledge Format (OKF v0.2)
hamiGenZ implements the **Open Knowledge Format (OKF v0.2)** specification as its structured knowledge foundation:
1. **Durable Knowledge Units:** Located under `data/okf/`, knowledge is stored as versioned Markdown files with rich YAML frontmatter, capturing concept IDs, authoritative sources (`verified: {by, at}`), and explicit concept relationships (`links`).
2. **Canonical Domain Truth:** Rather than hoping an embedding model retrieves the correct page count for an e-Passport (e.g. 34 vs 66 pages) from an arbitrary chunk, OKF concept files define canonical, machine-validated facts.
3. **Bounded Graph Traversal:** When a query touches related administrative workflows (e.g., citizenship prerequisites for passport applications), the OKF engine traverses typed links up to bounded depth to build a cohesive evidence package.

---

## 3. End-to-End System Architecture

```
                                  ┌────────────────────────┐
                                  │      User Browser      │
                                  │ Next.js 16 + React 19  │
                                  └───────────┬────────────┘
                                              │ (REST API)
                                  ┌───────────▼────────────┐
                                  │    FastAPI Backend     │
                                  │      (Python 3.12)     │
                                  └───────────┬────────────┘
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      │                                               │
           ┌──────────▼──────────┐                         ┌──────────▼──────────┐
           │   Document Pipeline │                         │    Query Router     │
           │ • PyMuPDF / Plumber │                         │ • OKF Structural KB │
           │ • Tesseract (nep)   │                         │ • Document Evidence │
           │ • Sentence Chunker  │                         │ • Official Registry │
           │ • FAISS Vector Store│                         │ • Trilingual Parser │
           └──────────┬──────────┘                         └──────────┬──────────┘
                      │                                               │
                      └───────────────────────┬───────────────────────┘
                                              │
                                  ┌───────────▼────────────┐
                                  │  Evidence Preparation  │
                                  │  Prompt Injection Guard│
                                  │  Untrusted Delimiters  │
                                  └───────────┬────────────┘
                                              │
                                  ┌───────────▼────────────┐
                                  │     Ollama Runtime     │
                                  │       (qwen3:8b)       │
                                  └───────────┬────────────┘
                                              │
                                  ┌───────────▼────────────┐
                                  │   Verification Layer   │
                                  │ • Grounding Validation │
                                  │ • Contradiction Check  │
                                  │ • Citation Attribution │
                                  └───────────┬────────────┘
                                              │
                                  ┌───────────▼────────────┐
                                  │ Final Grounded Answer  │
                                  │ + Interactive Citations│
                                  └────────────────────────┘
```

### Component Breakdown

1. **Frontend Workspace (`frontend/`):**
   - Built with Next.js 16 (Turbopack, TypeScript) and React 19.
   - Interactive split-screen: document preview with dynamic citation highlighting on the left, multi-level explanation panel (Original, Simple, Very Simple) on the right.
   - Zero telemetry leaks: compiled as a static client with configurable API backend routing.

2. **Ingestion & OCR Pipeline (`backend/pipeline.py`, `backend/ocr.py`):**
   - Dual-engine parsing: `pdfplumber` and `PyMuPDF` for digital documents; Tesseract 5.x with custom Nepali language data (`nep.traineddata`) for scanned images.
   - Automated script selector: tests Devanagari character densities to select between pure Nepali and bilingual OCR modes.

3. **Multilingual Vector Engine (`backend/vector_store.py`):**
   - Powered by `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384-dimensional dense vectors).
   - FAISS CPU indexes stored per document, with vector model checksums to eliminate model-switch index corruption.

4. **Prompt Injection Defense (`backend/prompt_guard.py`):**
   - Sanitizes untrusted user documents before constructing LLM context.
   - Strips zero-width unicode smuggling characters and system-role hijacking patterns.
   - Wraps retrieved chunks inside isolated `<evidence>` blocks with explicit system boundaries.

5. **Verification & Grounding (`backend/verification.py`):**
   - Secondary validation pass comparing LLM output against retrieved source chunks.
   - Rejects unsupported hallucinations: if evidence does not substantiate a claim, the system responds: *"I could not verify this from an authoritative source."*

---

## 4. Implementation Status

### Implemented (Verified in Active Codebase)
- **Open Knowledge Format (OKF v0.2) Layer:** Conformance validator (`backend/okf_validator.py`), YAML frontmatter parser, graph link traversal, and concept router covering Nepal Passport, Citizenship, National ID, Voter ID, and form-fill guidelines.
- **Bilingual OCR Pipeline:** Dual-engine OCR with Tesseract 5.x (using `nep.traineddata` and `eng.traineddata`) and PyMuPDF/pdfplumber, with automated Devanagari script detection.
- **Multilingual Vector Retrieval:** FAISS CPU dense vector index populated by `paraphrase-multilingual-MiniLM-L12-v2` (384-dim) with model-switch checksum protection.
- **Prompt Injection Defense:** Evidence isolation wrapping untrusted document text in `<evidence>` delimiters, role hijack neutralization, and zero-width unicode character stripping.
- **Grounding & Contradiction Verification:** Secondary inference layer that compares LLM responses against retrieved source passages and enforces refusal on ungrounded claims.
- **Multi-Tier Explanation Engine:** Three selectable simplification tiers (Original Text, Simple Summary, Bullet Breakdown) with trilingual language handling (Devanagari, Romanized Nepali, English).
- **Split-Pane Next.js 16 Workspace:** Responsive desktop, tablet, and mobile interface with interactive document viewing, dynamic citation clicking, and empty-state guidance.
- **Comprehensive Test Suite:** **282 passing unit, pipeline, security, and golden query tests** via `pytest`.
- **Action Layer (Form Assistance & Action Extraction):** `POST /actions` endpoint (action_extractor.py) extracts requirements (checklists), deadlines, fees, eligibility, next steps, and official links from pasted text or a document's retrieved evidence; LLM structured extraction cross-checked against deterministic regex hints; Nepali-aware normalization (Devanagari digits, day-first dates, currency); official-link safety (only gov.np / org.np / edu.np URLs ever displayed).
- **Official Source Answering:** `/ask-general` endpoint answers official-information questions (fees, procedures, laws, deadlines) from VERIFIED REGISTRY SOURCES via a local knowledge cache — evidence from curated sources only, SSRF-safe, never model memory dressed as official (PR-012).
- **Official Source Registry:** Curated registry of 10 authoritative Nepali sources (passport, national ID/civil registration, immigration, traffic, laws, judiciary, tax, citizenship, supreme court, govt portal) with full metadata (organization, domain, title, category, source type, authority level, verified status, current/outdated status) (PR-011).
- **Evaluation System:** Gold dataset (12+ human-verified cases across 11 categories with alternative-form key facts, forbidden facts, and sentence-level negation guards), retrieval benchmark (Hit@k / MRR / negative probes across English, Nepali, romanized, mixed), explanation evaluator (deterministic fact checks, no LLM judge in CI) — results recorded in docs/EVALUATION.md.
### Planned (Future Roadmap)
- **Offline Standalone Desktop Executable:** Packaging the frontend and local inference runtime into a self-contained Tauri/Electron desktop application for remote civic workers without internet connectivity.
- **Government Gazette Web Scraping:** Automated indexing pipeline for new circulars from official `.gov.np` portals.

---

## 5. User Experience & Responsive Design

The hamiGenZ workspace provides an accessible interface engineered to handle complex documents gracefully across screen sizes:

```
┌──────────────────────────────────────┬──────────────────────────────────────┐
│ Document Viewer                      │ Grounded Explanation Panel           │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ [Page 1 / 3]                         │ [Original] [Simple] [Very Simple]    │
│                                      │                                      │
│ "...citizenship certificate is       │ Verified Answer:                     │
│ required to verify applicant's date  │ You must present your original       │
│ of birth and permanent residency..." │ citizenship certificate to prove     │
│ [Citation 1 highlighted]             │ permanent residency. [Citation 1]    │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

*Desktop and mobile layouts tested and verified across 375px (mobile), 768px (tablet), 1024px, 1280px, and 1440px viewport widths.*

---

## 6. Quick Start & Local Development

### Prerequisites
- **Python:** 3.12+
- **Node.js:** 18+ (tested with v20+)
- **Ollama:** Installed and running locally (`ollama pull qwen3:8b`)
- **Tesseract OCR:** Installed with `nep` (Nepali) and `eng` (English) trained data.
  - Windows: Install via UB-Mannheim and install Nepali language data.
  - Linux: `sudo apt install tesseract-ocr tesseract-ocr-nep tesseract-ocr-eng`

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/omwe77/hamiGenz.git
cd hamiGenz

# Create and activate Python virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

The API documentation will be available at `http://localhost:8000/docs`.

### 2. Frontend Setup

```bash
# In a separate terminal, navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```

Open `http://localhost:3000` to access the interactive workspace.

---

## 7. Environment Variables

Create a `.env` file in the project root:

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b

# Embedding Configuration
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# Security & CORS
FRONTEND_ORIGIN=http://localhost:3000
MAX_UPLOAD_SIZE_MB=50

# Storage Paths
UPLOAD_DIR=data/uploads
VECTOR_DIR=data/vectors
SQLITE_DB_PATH=data/hamigenz.db
```

---

## 8. Verification & Test Suite

hamiGenZ maintains a strict test-driven development workflow:

```bash
# Run the full backend test suite (282 tests)
pytest tests/ -v

# Run OKF specification conformance validator directly
python -m backend.okf_validator

# Build and type-check the Next.js frontend
cd frontend
npm run build
```

---

## 9. Limitations & Boundary Conditions

- **Local Compute Demands:** Running `qwen3:8b` via Ollama requires at least 8 GB of unified RAM / VRAM for acceptable inference latency.
- **Scanned Document Quality:** Extreme degradation, physical tears, or blurred mobile photos may reduce OCR accuracy; the pipeline warns the user when OCR confidence falls below 60%.
- **No Direct Filing:** hamiGenZ provides explanatory guidance and verified criteria; it does not directly submit citizen applications to government portals.

---

## 10. License & Attribution

- **License:** MIT License © [Om Dangol](https://github.com/omwe77)
- **Knowledge Specification:** Built in conformance with the Open Knowledge Format (OKF v0.2).
