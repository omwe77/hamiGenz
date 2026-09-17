# hamiGenZ Changelog

## Unreleased (fix/ocr-integration-tests)

### Fixed
- **Test teardown no longer deletes `data/`**: `TestFullPipeline` previously walked
  the shared `data/` directory in teardown and removed tracked tessdata models and
  test PDFs. It now runs in an isolated temp directory.
- `/endpoints` route crashed (untyped `request` parameter, wrong return annotation);
  it now renders the live route index correctly with endpoint docstrings.
- `/documents/{doc_id}/search-text` was POST but the frontend called GET — unified
  on GET.
- Removed wildcard `allow_origins=["*"]` combined with `allow_credentials=True`
  (invalid/unsafe combination); CORS is now an explicit origin allowlist
  (`FRONTEND_ORIGIN`, localhost variants, optional `CORS_EXTRA_ORIGINS`).
- Removed dead `backend/admin_routes.py` (imported nonexistent `get_pipeline` /
  `_session_dirs`, never registered).
- Removed duplicate `contextlib`/`pathlib` imports and unused `_get_session_id`.
- Document viewer: rendered one pager per page (each with its own navigation);
  now a single continuous viewer with page anchors.
- Citation excerpts never matched raw page text (backend chunks are
  whitespace-normalized); highlighting now falls back to progressively shorter
  word-boundary snippets.
- Search-match highlights were applied in the wrong coordinate space (context-window
  offsets vs page text); now aligns on the matched term itself.
- "Explain this" used a stale `handleExplain` closure (ran the previous input);
  now explains the current selection directly.
- Workspace loading stages were declared after use and never visible; fixed state
  order and made progress announcements screen-reader friendly (`aria-live`).

### Added
- Scanned-page images now display inside the document viewer (was metadata-only).
- Search: debounced queries, match navigation (prev/next), active match scrolling.
- Clickable example prompts in the explain empty state (empty-state teaching).
- Responsive workspace grids (`ws-grid-2`, `ws-grid-3`) with tablet/mobile
  breakpoints; accessible labels on icon-only buttons.

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
