# hamiGenZ Changelog

## Unreleased (fix/ocr-integration-tests)

### Added — Form understanding (PR-010)
- `POST /forms/detect`: heuristic form detection (field labels, checkbox
  patterns, form keywords — English + Nepali) with page-anchored field
  extraction; cheap, no LLM call
- `POST /forms/explain-field`: grounded per-field explanation — what the
  field means, what belongs there, common mistakes, sample format, and a
  clearly-marked SAMPLE (FOR EXPLANATION ONLY / NOT FOR SUBMISSION)
- Anti-fabrication guards: examples use generic placeholders unusable as
  real identity data; long digit sequences are scrubbed from examples;
  the LLM must quote the field's own wording as evidence
- Degraded mode falls back to quoting the form's own wording
- Workspace UI: FormPanel in the text-explain tab (pasted text) and the
  document tab (active document) — field chips with page numbers, per-field
  explanations, SAMPLE frame, evidence box
- tests/test_forms.py: 18 offline tests with realistic Nepali citizenship
  application + English passport form samples; endpoint verified live
  (Nepali field detection + grounded Nepali explanation)

### Added — Action layer (PR-009)
- `POST /actions` endpoint: extracts requirements (checklist), deadlines,
  fees, eligibility, next steps, and official links from pasted text or a
  document's retrieved evidence
- `action_extractor.py`: LLM structured extraction cross-checked against
  deterministic regex hints (currency amounts, day-first dates, official
  URLs) — fees/dates the LLM reports that regex cannot find in the source
  are flagged `unverified` instead of silently trusted
- Nepali-aware normalization: Devanagari digit conversion, day-first date
  parsing with month/day disambiguation, idempotent currency
  canonicalization (रु / Rs. / NPR)
- Official-link safety: only http(s) URLs on Nepali official domains
  (gov.np / org.np / edu.np) are ever displayed; lookalike hosts rejected
- Degraded mode: if the LLM is unavailable, falls back to regex hints
  (`meta.status: hints_only`) rather than failing
- Workspace UI: "What should I do?" ActionPanel in both the text-explain
  and document tabs — checkbox requirements, dated deadlines, fee badges,
  numbered next steps, rel=nofollow official links
- tests/test_actions.py: 25 offline tests (normalization, hints, URL
  safety, hallucination guards); endpoint verified live end-to-end

### Security (development-phase hardening)
- Upload hardening: magic-byte content validation (declared MIME ignored),
  user filenames never touch disk (`<uuid>.<sanitized-ext>`), page-count
  limit (200) with rollback, malformed documents fail with a clean 400
- Path containment: document routes verify stored filepaths resolve inside
  the upload directory; page numbers bounds-checked; doc_id validated
  before vector retrieval
- Rate limiting: dependency-free per-IP sliding-window limiter on /upload,
  /ask, /explain, /ask-general, search-text (env-configurable, 429 +
  Retry-After)
- Prompt-injection defense: evidence sanitized + wrapped in untrusted-data
  delimiters; system preamble enforces instruction hierarchy (documents
  are data, never instructions) — PR-042
- CORS moved to an explicit origin allowlist (no wildcard + credentials)
- LLM outages return a clean 503 instead of leaking errors
- docs/SECURITY.md tracks implemented vs planned hardening

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
