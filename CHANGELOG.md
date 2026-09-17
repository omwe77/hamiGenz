# hamiGenZ Changelog

## Unreleased (fix/ocr-integration-tests)

### Fixed — Homepage UX audit (PR-015/016/019)
- **Critical: all four "Try hamiGenZ" CTAs pointed to a nonexistent
  `#open-workspace` anchor** — the homepage→workspace journey was broken;
  now links to the real `/workspace` route (verified in served HTML)
- Removed nav link to a nonexistent `About` section
- Hero is now a semantic `<h1>` (was a div — accessibility + SEO)
- Mobile: story section's 2-column grid + sticky document card now
  collapse to a single column; oversized hero heading scales down
- Robustness: if anime.js fails to load (or `prefers-reduced-motion`),
  hero/story content is force-revealed instead of staying at opacity 0
- Trust copy: removed `localhost:8000` developer-speak from the demo
  section (now states the privacy benefit in user language)

### Changed — Embedding model switched on benchmark evidence (PR-014)
- New evaluation system: gold dataset (12+ human-verified cases across 11
  categories with alternative-form key facts, forbidden facts, and
  sentence-level negation guards), retrieval benchmark (Hit@k / MRR /
  negative probes across English, Nepali, romanized, mixed), explanation
  evaluator (deterministic fact checks, no LLM judge in CI), and 16
  dataset-integrity self-consistency tests
- Benchmark verdict: all-MiniLM-L6-v2 scored Hit@1 0.22 / MRR 0.41 with a
  **0.33 false-match rate** and 0.00 Hit@1 on English→Nepali queries;
  paraphrase-multilingual-MiniLM-L12-v2 scores Hit@1 0.72 / MRR 0.81 with
  zero false matches — default switched accordingly (same 384-dim,
  local, free)
- Model-switch safety: `data/vectors/embed_model.txt` stamp; on mismatch,
  docs are re-embedded from stored chunk text automatically (or
  quarantined when not re-embedable) instead of silently serving garbage
  vectors; manual `POST /upload?reindex_doc_id=` also available
- **Fixed: Nepali uploads crashed on Windows** — vector metadata JSON was
  written without `encoding="utf-8"` (cp1252 cannot encode Devanagari);
  all JSON reads/writes in the vector store now UTF-8
- Fixed: `/ask` 500 — `format_answer` returns `language` but the response
  model required `language_used` (missing-field mapping added)
- See docs/EVALUATION.md for full results and the decision rationale

### Added — Official-source answering (PR-012)
- `/ask-general` now answers official-information questions (fees,
  procedures, laws, deadlines) from VERIFIED REGISTRY SOURCES via a local
  knowledge cache — evidence comes only from curated sources, never
  arbitrary URL fetches (SSRF-safe), and never from model memory dressed
  up as official
- Full flow: intent detection (EN/NP/romanized) → category → registry
  source → cached evidence retrieval → freshness check (verification age,
  cache age, current/outdated status) → grounded generation →
  VerificationLayer re-check → answer + authority-labeled sources
- Honest states: no cached source → "could not verify" + the official
  source to consult; LLM down → raw official evidence shown unprocessed;
  retrieval failure → degrades safely (no fake-official answers)
- UI: OFFICIAL SOURCE provenance badge + OfficialSourcesCard showing
  organization, authority, excerpt, content date, and stale/unknown
  freshness warnings in plain language
- Seed knowledge cache: passport fees/documents/appointment, driving
  license procedure/fees, national ID + birth registration
- 27 new tests (authority, freshness, claims, provenance, failures);
  121 passed / 1 skipped total; live-verified end to end

### Added — Official source registry (PR-011 foundation)
- Curated registry of 10 authoritative Nepali sources (passport, national
  ID/civil registration, immigration, traffic, laws via Nepal Law
  Commission, judiciary, tax, citizenship, supreme court, govt portal)
  with full metadata: organization, domain, title, category, source type,
  authority level, verified status + date, current/outdated status
- Authority boundary is the REGISTRY, never the TLD: org.np/edu.np are
  open-registration domains and even uncurated *.gov.np hosts classify as
  `unverified` until reviewed
- `GET /knowledge/sources` (category filter) and `GET /knowledge/classify`
- Action-panel links now display "✓ verified official" or an explicit
  "unverified source" warning based on registry classification
- 20 new registry tests (94 passed / 1 skipped total)

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
