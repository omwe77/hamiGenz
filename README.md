# hamiGenZ — Nepal's AI Information & Document Understanding Platform

Tagline: "Don't understand it? Ask hamiGenZ."

## Project Structure

```
hamigenz/
├── backend/          # Python + FastAPI backend
├── frontend/        # Next.js/React frontend
├── data/            # Uploaded documents, vector DB, knowledge base
├── tests/           # Test suite
└── docs/            # Documentation
```

## Phase 1 MVP Scope

- File upload (PDF, images)
- PDF text extraction (pdfplumber/pymupdf)
- Basic OCR (Tesseract via pytesseract)
- Document chunking + local embeddings
- Local vector storage (FAISS)
- Question answering via Ollama (qwen3:8b)
- English/Nepali/Romanized Nepali support
- Source/page citations
- Simple explanation engine
- Basic grounding validation
- Basic form-field explanation
- Publicly usable FastAPI + minimal UI interface
- Fully local/free operation

## Tech Stack

- **Backend:** Python 3.11 + FastAPI + Uvicorn
- **LLM:** Ollama + qwen3:8b (already running locally)
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2 or similar free model)
- **Vector DB:** FAISS (local, no server needed)
- **OCR:** pytesseract + Tesseract OCR
- **PDF:** pdfplumber + pymupdf (fitz)
- **Frontend:** Next.js + React (minimal UI for MVP)
- **DB:** SQLite (metadata), FAISS (vectors)

## Development Phases

1. **Phase 1 — MVP:** Core document RAG pipeline, local/free, publicly usable
2. **Phase 2 — Official Nepal Knowledge:** Curated KB (passport, NID, traffic, govt services)
3. **Phase 3 — Action Features:** Checklists, deadline/fee extraction, form filling help
4. **Phase 4 — Strong Verification:** Claim extraction, contradiction detection, confidence scoring
5. **Phase 5 — Expansion:** PWA, camera scanning, voice, API, multi-language

## Quality Priority

Accuracy > Grounding > Usefulness > Simplicity > Visual polish

Prefer: "I could not verify this from an authoritative source."
Over: confident but unsupported answer.
