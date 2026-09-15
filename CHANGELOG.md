# hamiGenZ Changelog

## Phase 1 MVP (current)

- Document upload (PDF, PNG, JPG, TIFF)
- PDF text extraction (pdfplumber + PyMuPDF)
- OCR for scanned documents (Tesseract, Nepali + English)
- Sentence-level chunking with overlap
- Local embeddings (sentence-transformers all-MiniLM-L6-v2)
- FAISS vector storage per document
- Ollama LLM (qwen3:8b)
- Grounding validation (claim extraction vs evidence)
- Explanation engine (structured, simple language)
- Language detection (Nepali, English, Romanized Nepali, mixed)
- Form-filling explanation mode with SAMPLE markers
- FastAPI endpoints: /upload, /ask, /ask-general, /documents, /health
- Fully local and free — no paid APIs

## Upcoming Phases

- Phase 2: Official Nepal knowledge base (passport, NID, traffic, govt services)
- Phase 3: Action features (checklists, deadline/fee extraction, form filling)
- Phase 4: Strong verification (contradiction detection, confidence scoring)
- Phase 5: Expansion (PWA, camera scanning, voice, API)
