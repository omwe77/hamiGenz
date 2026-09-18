# hamiGenZ — Architecture Document

## System Overview

hamiGenZ is a local-first AI document understanding platform for Nepal. It
accepts PDF/PNG/JPG/TIFF uploads, extracts text (with OCR for scanned
documents), chunks and embeds content, then answers questions using a local
LLM grounded in the retrieved evidence.

```
User → Frontend (Next.js) → FastAPI Backend → Ollama (qwen3:8b)
                                     ↓
                          Tesseract OCR / pdfplumber / PyMuPDF
                                     ↓
                          sentence-transformers → FAISS
```

## Components

### Frontend (`frontend/`)

- Next.js 16 + React 19, TypeScript
- Static export (`output: "export"`) — no server-side rendering
- Anime.js scroll storytelling on homepage
- Workspace: text explain, document upload/viewer, action extraction, form understanding
- API client in `src/lib/hamigenz-api.ts` — all calls go through one base URL

### Backend (`backend/`)

- FastAPI + Uvicorn, Python 3.12
- Endpoints: /health, /upload, /ask, /ask-general, /explain, /actions, /forms/*, /knowledge/*, /documents/*, /endpoints
- Lifespan init: embedding service, vector store, chunker, metadata store, Ollama, pipeline, validator, verification, explainer, action extractor, form service, official answer service
- CORS: explicit origin allowlist (env `FRONTEND_ORIGIN`)

### LLM (`ollama` + `qwen3:8b`)

- Local Ollama server on port 11434
- Model: qwen3:8b (default, configurable via `OLLAMA_MODEL`)
- Used for: answer generation, explanation, verification layer, action extraction, form explanation, official-source answering

### Embeddings

- Model: paraphrase-multilingual-MiniLM-L12-v2 (384-dim, local, free)
- Selected over all-MiniLM-L6-v2 on retrieval benchmark: Hit@1 0.72 vs 0.22, MRR 0.81 vs 0.41, false-match rate 0.00 vs 0.33
- sentence-transformers library

### Vector Store

- FAISS CPU index per document
- Stored in `data/vectors/`
- Model stamp file guards against silent vector corruption on model switch
- SQLite metadata in `data/hamigenz.db`

### OCR

- Tesseract 5.x with nep, eng, osd traineddata
- Multi-config selector: tries nep → eng+nep → eng, picks best by Nepali character count
- Nepali-only model for Devanagari (eng+nep garbles it)

### Document Processing

- PDF: pdfplumber + PyMuPDF (fitz) for text, PyMuPDF for page images
- Images: Tesseract OCR
- Chunking: sentence-level, 500 chars + 50 overlap
- Upload validation: magic bytes, 50 MB max, UUID filenames, path containment, 200 page max

### Official Source Registry

- Curated registry of 10 authoritative Nepali sources
- `/knowledge/sources` + `/knowledge/classify`
- `/ask-general` uses registry for official-information questions

## Data Flow (Ask)

```
1. User types question in workspace
2. Frontend POSTs /ask with question + optional doc_id + language hint
3. Backend detects language
4. Pipeline retrieves top-5 evidence chunks from FAISS
5. Evidence wrapped in untrusted-data delimiters (prompt injection defense)
6. LLM generates answer (form mode or document mode prompt)
7. VerificationLayer checks grounding, detects contradictions
8. If contradictions found, re-prompt for corrected answer
9. ExplanationEngine formats with citations, level, language
10. Frontend renders answer + citations + evidence highlights
```

## Data Flow (Upload)

```
1. User selects file in workspace
2. Frontend POSTs /upload with multipart file
3. Backend validates: size, magic bytes, extension
4. File saved as <uuid>.<ext> in data/uploads/
5. Pipeline: extract text → chunk → embed → index in FAISS
6. Metadata stored in SQLite
7. Response: doc_id, filename, pages, chunks, language_hint
```

## Deployment Targets

| Target | Status | Where |
|---|---|---|
| Local development | Current | localhost:3000 + localhost:8000 |
| Azure staging | This phase | Static Web Apps + B2ms_v2 VM |
| Production | Future phase | TBD |

## Staging Architecture

See `docs/DEPLOYMENT.md` for full staging deployment guide.

```
Azure Static Web Apps (Free)  →  https://hamigenz-staging.<region>
        ↓ API calls
Azure VM Standard_B2ms_v2 (East US)
        ├── Nginx (HTTPS, port 443)
        ├── FastAPI + Uvicorn (port 8000)
        ├── Ollama + qwen3:8b (port 11434, localhost only)
        ├── Tesseract + traineddata
        ├── sentence-transformers
        └── data/ (uploads, vectors, db) on managed disk
```
