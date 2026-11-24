# hamiGenZ — Release & Recovery Ledger

## Milestone 1 (M1): Repository Hygiene & Test Suite Stabilization

### Completed Tasks

#### [M1-TASK-01] Preserve Changes, Git Workflow Remediation & Security Test Verification
- **Status:** Complete (Verified & Pushed)
- **Date:** 2026-11-17
- **Owner:** Antigravity (Lead Orchestrator)
- **Branch:** `fix/security-test-suite-anyio`
- **Commit SHA:** `c6bfbf44cf4aca5c5dce28527251e2760a49d1ab`
- **Actions Taken:**
  1. **Working Copy Relocation:** Relocated working tree from OneDrive-synced path (`C:\Users\LENOVO\OneDrive - London Metropolitan University\Documents\my_projects\hamigenz`) to non-synced location (`C:\Projects\hamiGenz`).
     - *Root Cause of Git Lock Failure:* Verified filesystem ACL and attributes. The OneDrive mirror had marked `.git` with `ReadOnly`, `Archive`, and `ReparsePoint` attributes alongside an inherited `(D;CIID;DT;;;WD)` (Deny Everyone DeleteSubdirectoriesAndFiles) access control entry. This prevented Git from creating/renaming temporary lock files. Cleared ReadOnly attributes and pruned stale worktrees.
  2. **Security Test Verification (`tests/test_security.py`):**
     - Replaced `asyncio.run(run())` with `anyio.run(run)` across all three ASGI transport tests (`test_upload_save_exception_hides_system_paths`, `test_fill_preview_exception_hides_system_details`, `test_set_form_fields_invalid_payload_sanitized`).
     - Resolved event loop conflict where Starlette/FastAPI ASGI transport deadlocked under fresh `asyncio.run` threadpool invocations on Windows.
     - Corrected `fill-image` test payload from `{"values": {"name": "Test"}}` to match the Pydantic schema `{"values": [{"label": "name", "value": "Test"}]}`.
  3. **Verification Results:**
     - Focused Suite: `pytest tests/test_security.py -v` -> 10 passed in 5.91s.
     - Security & Integration Regression: 127 passed in 82.86s (`test_security.py`, `test_phase1_security.py`, `test_upload_ingress.py`, `test_fill_image.py`, `test_railway_ip_and_health.py`, `test_prompt_guard.py`, `test_reindex_safety.py`).
     - GitHub Actions CI (Run `44110243612`):
       - Backend CI (Python 3.11): Passed (2m39s)
       - Frontend CI (Node 24): Passed (1m30s)
       - Docker Validation (Root Context): Passed (1m4s)

#### [M1-TASK-02] Pytest Root Collection Fix (pytest.ini)
- **Status:** Complete (Verified)
- **Date:** 2026-11-17
- **Owner:** Hermes / Team
- **Commit SHA:** `e293713` (`chore(test): add pytest.ini testpaths to fix root collection collision`)
- **Actions Taken:**
  - Added root `pytest.ini` with `testpaths = tests` configuration.
  - Eliminated root-level directory collection collisions.
- **Verification Results:**
  - 511 items cleanly collected, 0 collection errors.

#### [M1-TASK-03] Full Codebase Test Suite Execution
- **Status:** Complete (Verified)
- **Date:** 2026-11-17
- **Verification Results:**
  - Executed full test suite locally against Python 3.12.10 on Windows runtime.
  - Result: **510 passed, 1 skipped, 0 failures** (6 warnings) across 511 collected tests in 68.90s.
  - Verified zero cross-module regressions across all unit, security, ingress, concurrency, and pipeline test modules.

#### [M1-TASK-04] PR Preparation & Documentation
- **Status:** Complete (Prepared for Review)
- **Date:** 2026-11-17
- **Artifact:** `pr-body.md`
- **Target:** `main` from branch `fix/security-test-suite-anyio` (Final Head Commit `3ade165`)
- **Summary:** Documented 26 changed files, diff statistics (+2816 / -514), key architectural & security changes, and test execution evidence.

#### [M1-TASK-05] PR Submission, CI Gate & Trunk Merge
- **Status:** Complete (Merged into `main`)
- **Date:** 2026-11-17 / 2026-11-22
- **PR:** https://github.com/omwe77/hamiGenz/pull/3
- **Final Head SHA:** `a2bd0e5ebd4e57ba197cd5cd692461bbf449b9f0`
- **Main Merge Commit:** `68d79e3ec24c6403369611a10ea797808e92bac9`
- **CI Run on Main (`44985014326`):**
  - Backend CI (Python 3.11): ✅ SUCCESS
  - Frontend CI (Node 24): ✅ SUCCESS
  - Docker Validation: ✅ SUCCESS
  - Vercel Preview: ✅ SUCCESS
- **Local Full Suite Verification on `a2bd0e5`:**
  - `pytest -q --tb=short`: 511 passed, 1 skipped across 512 tests (905.65s, Python 3.12.10 / Windows)
- **Defects Fixed in M1:**
  - [P2] `_BodyTooLargeError` re-raised from `upload_document` → 413 preserved (not swallowed into 400)
  - [P2] `UPLOAD_DIR.mkdir()` before staging file open → no FileNotFoundError on clean checkouts
  - [P2] Docker Non-Root Hardening: Created dedicated `hamigenz` user (UID/GID 10001), assigned `/app` and `/home/hamigenz` ownership, configured `USER 10001:10001`, and verified in CI (UID 10001, writable paths, `/health` 200 OK)
  - [P3] Vacuous `or True` removed from traversal assertion in `test_security.py`
  - [P3] `test_T3_streaming_body_over_limit_endpoint_yields_413` added to verify endpoint-level 413

---

### Milestone 1 Status: COMPLETE (Merged into `main` at `68d79e3`)

All M1 quality gates, test suite migrations, security hardening, and CI baselines are established, passing, and merged into `main`.

---

---

## Milestone 2 (M2): Pipeline Reliability & OCR Hardening

### Tasks

#### [M2-TASK-01] Nepali OCR Engine Reliability & Fallback Hardening
- **Status:** Complete (Verified)
- **Date:** 2026-11-18
- **Owner:** Antigravity (Lead Orchestrator)
- **Branch:** `feat/m2-ocr-reliability`
- **Files Modified:**
  - `backend/ocr_engines.py`: dynamic discovery, actionable diagnostics (`diagnose_tesseract()`), graceful fallback, Devanagari preference scoring, `local_files_only=True` for offline safety.
  - `backend/requirements.txt`: pinned `easyocr==1.7.2` and `transformers==4.57.6`.
  - `tests/test_ocr.py`: wrapped manual diagnostics in `if __name__ == "__main__":` guard and eliminated hardcoded paths.
  - `tests/test_ocr_engines.py`: 33 deterministic unit tests covering Tesseract detection, fallback cascades, Devanagari character counting, and offline enforcement.
- **Verification Results:**
  - Automated tests: `pytest tests/test_ocr_engines.py -v` -> 29 passed, 4 skipped (integration checks when system binary unconfigured), 0 failed.
  - Zero network activity: verified `local_files_only=True` prevents downloads during OCR requests.
  - Document understanding pipeline backwards compatibility preserved.

---

#### [M2-TASK-02] Document Processor Extraction Resilience & Error Boundary
- **Status:** Complete (Verified)
- **Date:** 2026-11-18
- **Owner:** Antigravity (Lead Orchestrator)
- **Branch:** `feat/m2-ocr-reliability`
- **Files Modified:**
  - `backend/document_processor.py`: Context-managed PDF and PIL document lifetime, corruption and zero-byte protection, password-protected PDF check, zero-page check, bounded `max_pages=200`, out-of-bounds page rendering guard returning `None`/`[]`/`""`, Unicode NFC normalization with stdlib `unicodedata`, and integrated OCR cascade fallback.
  - `tests/test_document_processor.py`: 25 deterministic unit tests covering nonexistent files, empty/corrupt files, 0-page PDFs, max-page bounds, clean text extraction, out-of-bounds rendering, upload path neutralization, custom doc IDs, Unicode NFC normalization, and OCR fallback delegation.
- **Verification Results:**
  - Automated tests: `pytest tests/test_document_processor.py -v` -> 25/25 passed in 6.12s.
  - Combined suite: `pytest tests/test_document_processor.py tests/test_ocr_engines.py tests/test_security.py -v` -> 68 passed, 0 failed.
  - Zero unclosed file handles; robust bounds enforcement on all rendering methods.

---

#### [M2-TASK-03] Vector Store / Generation-Safe Reindexing Lock & Cleanups
- **Status:** Complete (Verified)
- **Date:** 2026-11-18
- **Owner:** Antigravity (Lead Orchestrator)
- **Branch:** `feat/m2-ocr-reliability`
- **Files Modified:**
  - `backend/vector_store.py`: Enhanced `VectorStore.remove_document` to automatically discover and purge all generation-specific artifacts (`{doc_id}_g*.faiss`, `{doc_id}_g*_meta.json`) in addition to flat legacy files, preventing disk leakages during document deletion after staged re-indexing.
  - `tests/test_reindex_safety.py`: Added `test_T23_remove_document_purges_all_generation_artifacts` verifying complete multi-generation artifact removal.
- **Verification Results:**
  - Automated tests: `pytest tests/test_reindex_safety.py -v` -> 23/23 passed in 6.42s.
  - Ingress safety: `pytest tests/test_upload_ingress.py -q` -> 35/35 passed in 6.84s.
  - Pipeline ingestion: `pytest tests/test_pipeline.py -q` -> 13 passed, 1 skipped.

---

#### [M2-TASK-04] Official Source Registry & Verified Domain Validation
- **Status:** Complete (Verified)
- **Date:** 2026-11-18
- **Owner:** Antigravity (Lead Orchestrator)
- **Branch:** `feat/m2-ocr-reliability`
- **Files Modified:**
  - `backend/source_registry.py`: Hardened `find_by_domain` against port suffixes and trailing FQDN root dots, and hardened `classify_url` against embedded credentials (`user:pass@host` or phishing userinfo injection).
  - `tests/test_source_registry.py`: Added comprehensive unit tests for port handling, FQDN root dots, and embedded credential rejection.
- **Verification Results:**
  - Automated tests: `pytest tests/test_source_registry.py -v` -> 24/24 passed in 0.30s.
  - Official answer integration: `pytest tests/test_official_answer.py -v` -> 27/27 passed in 0.69s.
  - Action extraction URL safety: `pytest tests/test_actions.py -v` -> 25/25 passed in 0.62s.

---

### Milestone 2 Summary & PR Submission

All planned Milestone 2 tasks (`[M2-TASK-01]` through `[M2-TASK-04]`) and final QA hardenings were implemented and verified:
1. `[M2-TASK-01]`: Nepali OCR Engine Reliability, dynamic binary discovery, Devanagari preference scoring, offline safe loading (`download_enabled=False`, `local_files_only=True`), OCR cascade fallback, and reference Devanagari CER test fixture.
2. `[M2-TASK-02]`: DocumentProcessor extraction resilience, context-managed PDF/PIL lifecycle, zero-byte/corrupt/password protection, bounds enforcement (`max_pages=200`), out-of-bounds page rendering safety, and Unicode NFC normalization.
3. `[M2-TASK-03]`: Vector store generation-safe reindexing, multi-generation FAISS and metadata artifact cleanup on document deletion, and lock safety.
4. `[M2-TASK-04]`: Official source registry domain validation (`find_by_domain` port and root-dot handling) and URL credential defense (`classify_url` rejecting userinfo injection).
5. **CI Trigger, Test Isolation & Full Regression:**
   - Expanded `.github/workflows/ci.yml` `pull_request` triggers to support stacked branches.
   - Expanded regression matrix for document processor, OCR engines, and upload ingress.
   - Hermetic test fixtures isolating upload directories.
   - Full test suite: 580 passed, 1 skipped across 581 tests.

---

#### [M2-TASK-05] PR Retargeting, CI Gate & Trunk Merge
- **Status:** Complete (Merged into `main`)
- **Date:** 2026-11-22
- **PR:** https://github.com/omwe77/hamiGenz/pull/4
- **Branch:** `feat/m2-ocr-reliability`
- **Initial Target:** `fix/security-test-suite-anyio` (stacked)
- **Retargeted Target:** `main` (after M1 merge)
- **Synchronization Commit:** `c97e9cb` (`chore(merge): sync main into feat/m2-ocr-reliability`)
- **Final Head SHA:** `4b65b3f66d3a76c7794cfcbfc63b5ffb2963d458`
- **PR CI Run (`44989745711`):**
  - Backend CI (Python 3.11): ✅ SUCCESS
  - Frontend CI (Node 24): ✅ SUCCESS
  - Docker Validation: ✅ SUCCESS
- **Main Merge Commit:** `832341754d7d240e58c1b83d0d8cd030ad190496`
- **Post-Merge CI Run on Main (`45009228196`):**
  - Backend CI (Python 3.11): ✅ SUCCESS (2m13s)
  - Frontend CI (Node 24): ✅ SUCCESS (1m30s)
  - Docker Validation: ✅ SUCCESS (1m08s)
- **Ancestry Verification:**
  - Both M1 (`68d79e3ec24c6403369611a10ea797808e92bac9`) and M2 (`4b65b3f66d3a76c7794cfcbfc63b5ffb2963d458`) are confirmed direct ancestors of `origin/main` at `8323417`.
- **Agent-Reported Local Validation (Uncommitted Scratch Script):**
  - An 8-step component-level workflow was exercised via an ephemeral local script (`acceptance_workflow_demo.py`, not committed to git): synthetic bilingual document creation, PyMuPDF text extraction, reference Devanagari OCR fixture evaluation (`tests/ocr_tests/nep.png`), vector indexing, grounded citation retrieval, negative input rejection, and artifact deletion.
  - *Audit qualification:* The run verified offline LLM error handling (`LLMUnavailableError` / 503) because Ollama was offline on `localhost:11434`; live generative Qwen3:8b inference was not executed. Because the script and test artifacts were not committed to the repository, this constitutes agent-reported local validation rather than an independently verifiable acceptance test.

---

### Milestone 2 Status: COMPLETE (Merged into `main` at `8323417`)

All M2 quality gates, OCR and document processor reliability improvements, test matrices, and CI baselines are established, passing, and merged into `main`.

---

## Release Publication: v0.1.0 (Local-First Beta)

- **Release Version:** `v0.1.0`
- **Release Tag:** `v0.1.0`
- **Release Commit:** `832341754d7d240e58c1b83d0d8cd030ad190496`
- **Publication Date:** 2026-11-22
- **GitHub Release URL:** https://github.com/omwe77/hamiGenz/releases/tag/v0.1.0
- **Summary of Included Milestones:**
  - **M1 (Security & Ingress Hardening):** Bounded upload request size controls (52 MiB raw, 50 MiB file field), admission control (max 4 concurrent), AnyIO test reliability, non-root Docker runtime (UID/GID 10001).
  - **M2 (OCR & Pipeline Reliability):** Dynamic Tesseract discovery and Nepali fallback cascade, offline EasyOCR/TrOCR model loading safeguards, Unicode NFC normalization, DocumentProcessor resource/bounds safety, generation-aware FAISS cleanup, source registry URL hardening, expanded CI.
- **Operational Boundaries & Limitations:**
  - Local-first beta designed for local self-hosted execution; not a public multi-tenant hosted service.
  - Generative Q&A requires a locally running Ollama instance (`qwen3:8b`) with at least 8 GB RAM/VRAM; degrades gracefully to 503 when absent.
  - Nepali OCR verified on synthetic/reference fixtures; broad accuracy on real-world degraded scans remains unproven.
  - Railway persistent-volume permissions remain unverified; cloud deployment is deferred.
  - Public deployment at `hami-genz.vercel.app` is a client-side portfolio demonstration only.
