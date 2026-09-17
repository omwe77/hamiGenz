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
- **Verification layer (STEP 3):** contradiction detection, numeric confidence score (0–100), confidence band, unsupported-facts list, and automatic answer re-prompt when contradictions are found — wired into /ask and /explain
- Explanation engine (structured, simple language)
- Language detection (Nepali, English, Romanized Nepali, mixed)
- Form-filling explanation mode with SAMPLE markers
- FastAPI endpoints: /upload, /ask, /ask-general, /documents, /health
- Fully local and free — no paid APIs
- Multi-config OCR selector (tries nep, eng+nep, eng; picks best by Nepali char count)
- Nepali OCR uses Nepali-only Tesseract model (eng+nep garbles Devanagari text)
- Next.js 16 + React 19 frontend with Anime.js scroll storytelling
- AI workspace (Ask / Upload / Document modes)
- E2E integration test: passport PDF → 24 Q&A pairs, all passing
- Nepali OCR verification test (PSM 8 single-word mode)
- requirements.txt with pinned versions
- run.sh to start backend + frontend together

## Upcoming Phases

- Phase 2: Official Nepal knowledge base (passport, NID, traffic, govt services)
- Phase 3: Action features (checklists, deadline/fee extraction, form filling)
- Phase 4: Strong verification (contradiction detection, confidence scoring)
- Phase 5: Expansion (PWA, camera scanning, voice, API)
