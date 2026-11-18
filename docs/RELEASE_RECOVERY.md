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
- **Target:** `main` from branch `fix/security-test-suite-anyio` (Final Head Commit `84e7a01`)
- **Summary:** Documented 26 changed files, diff statistics (+2816 / -514), key architectural & security changes, and test execution evidence.

#### [M1-TASK-05] PR Submission & CI Gate
- **Status:** Complete (Verified Green on PR Head `84e7a01`)
- **Date:** 2026-11-17 / 2026-11-18
- **PR:** https://github.com/omwe77/hamiGenz/pull/3
- **Head SHA:** `84e7a017afadd932306bf1c1d8fc8a4ce004a508`
- **CI Run (`44121472236`):**
  - Backend CI (Python 3.11): ✅ SUCCESS
  - Frontend CI (Node 24): ✅ SUCCESS
  - Docker Validation: ✅ SUCCESS
  - Vercel Preview: ✅ SUCCESS
- **Merge Gate:** Awaiting explicit owner approval before merging into `main`.

---

### Milestone 1 Status: COMPLETE (Ready for Owner Merge Approval)

All M1 quality gates, test suite migrations, and CI baselines are established and passing.

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

### Next Milestone 2 Tasks

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

### Next Milestone 2 Tasks

1. **[M2-TASK-04] Official Source Registry & Verified Domain Validation:**
   - Audit `backend/official_sources.py` and URL validation for Nepal Government portals (`.gov.np`).
   - Harden source registry against schema drift, invalid schemes, and lookalike domains.
