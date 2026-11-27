# hamiGenZ — Milestone 4 (M4) Implementation Plan

**Status:** Proposed — Awaiting Implementation Approval  
**Baseline:** `main` @ `a22d047` (M3 closed, PR #7 merged at `160e661`)  
**Core Architecture:** **Open Knowledge Format (OKF v0.2)** — preserved as the primary knowledge representation and routing architecture (`okf` curated concept bundle, `document` section/FAISS retrieval, `general` official-source answering). M4 extends OCR accuracy, grounding verification, and security without replacing or relabeling OKF v0.2.

---

## 1. Architectural Guardrails & Non-Negotiables

1. **Preserve OKF v0.2 as the Core Architecture:**
   - Curated domain knowledge remains structured as cross-linked Markdown concept files with YAML frontmatter (`okf_bundle.py`, `okf_validator.py`), preserving document structure (`DocumentType`, `FormGuide`, `OCRRule`, `FieldDefinition`) rather than flattening curated knowledge into disconnected RAG chunks.
   - `/ask` routing (`okf` → `document` → `general`) and `official_answer.py` registry-first answering remain intact.
2. **Do Not Change the Default OCR Engine Prematurely:**
   - `tesseract` (`nep+eng`) remains the default primary OCR engine (`IMPLEMENTED_ENGINES = ("tesseract",)`).
   - Heavyweight deep-learning OCR dependencies (e.g., PaddleOCR / PaddlePaddle, Surya) must **not** be added to `backend/requirements.txt` or `Dockerfile` unless Phase 4A benchmarks on a locked real-world corpus prove lightweight preprocessing is insufficient and the image/RAM/CI cost is justified.
3. **No Deployment or Release Without Approval:**
   - No Railway staging deployment, Vercel production change, or GitHub release tag is authorized as part of M4 planning.

---

## 2. Dataset Licensing, Provenance & Privacy Rules

Any new evaluation corpus created in M4 (starting with Phase 4A `tests/evaluation/real_ocr_corpus/` and Phase 4B `tests/evaluation/gold_grounding/`) must satisfy all of the following rules before being committed:

| Rule | Requirement | Enforcement |
|---|---|---|
| **Zero PII / Real Citizen Data** | Real personal citizenship cards, passports, NID cards, tax receipts with real names/IDs, or user uploads must **never** be committed. | Manual + automated inspection before commit; `UPLOAD_DIR` and `VECTORS_DIR` remain `.gitignore`d. |
| **Permissive Provenance Only** | Only `CC0-1.0`, `Public Domain` Nepal Government public notices/gazettes, blank official form templates, or synthetically degraded/redacted public templates may be included. | Every corpus directory must include a `MANIFEST.json` recording `filename`, `source_url` (or `synthetic_from_public_template`), `license`, `collected_date`, and `pii_cleared: true`. |
| **Clear Synthetic vs. Real Labeling** | `eval_ocr.py` must continue tagging `dataset_type` explicitly (`"synthetic"` vs. `"real_public_notice"`), never conflating synthetic benchmarks with real-world scan accuracy. | Enforced in `eval_ocr.py` output schema and `tests/test_ocr_evaluation.py`. |

---

## 3. Dependency & Resource Budget Analysis

hamiGenZ targets local-first self-hosting (<= 8 GB RAM/VRAM alongside Ollama `qwen3:8b`) and strictly offline GitHub Actions CI (`TRANSFORMERS_OFFLINE=1`, `HF_HUB_OFFLINE=1`, `Backend CI` < 5 min, `Docker Validation` < 6 min).

| Candidate | License | Footprint / Resource Impact | M4 Decision |
|---|---|---|---|
| **`Pillow` + `pytesseract` (existing)** | HPND / Apache 2.0 | `0 MB` incremental (already installed) | **Default baseline** (`Phase 4A` first target). |
| **`opencv-python-headless`** | Apache 2.0 | ~35–50 MB wheel, no X11/GUI deps, CPU-only | **Evaluate in Phase 4A** only for deterministic deskew/binarization/denoise if Pillow-only preprocessing leaves a gap. |
| **`rank_bm25`** | Apache 2.0 | < 1 MB pure Python, negligible RAM | **Optional in Phase 4B** for exact-token lexical matching (Nepali numerals, form codes) alongside FAISS `document` retrieval. |
| **`PaddleOCR` (`PP-OCRv5` Devanagari mobile)** | Apache 2.0 (code & weights) | ~150–400+ MB runtime + model weights, C++ inference overhead | **Gated / Deferred:** Evaluate offline in a branch spike only if Phase 4A Tesseract + preprocessing fails to hit targets. |
| **`Surya OCR`** | Apache 2.0 code / **Modified AI Pubs OpenRAIL-M weights** | Heavy PyTorch/transformer weights; weight license restricts > \$5M entities | **Rejected for default bundle** due to weight license & footprint. |

---

## 4. Phased M4 Roadmap

**Phase 4A** is the first implementation milestone. **Phases 4B and 4C** are separately scoped and gated behind 4A completion and review.

---

### Milestone 4A (First Implementation Milestone): Real-World Nepali OCR Corpus & Lightweight Preprocessing

#### Scope
1. **Curate & Lock Real-World Public Corpus (`tests/evaluation/real_ocr_corpus/`):**
   - Collect 25–50 paired image/ground-truth samples (`.png`/`.jpg` + `.gt.txt`) from public-domain Nepal government notices, blank public forms, and realistic scan degradations (skew, stamps, low-DPI photocopies, uneven lighting), with `MANIFEST.json` provenance.
2. **Reproducible Benchmark Harness (`tests/evaluation/eval_ocr.py`):**
   - Run all comparisons on the **identical locked corpus**, identical Unicode NFC normalization (`unicodedata.normalize("NFC", ...)`), and identical CER/WER metric definitions.
   - Record per-case and aggregate CER, WER, median latency (ms/page), peak RSS memory, and engine/preprocessing configuration.
3. **Lightweight Preprocessing Pipeline (`backend/document_processor.py` / `backend/ocr_engines.py`):**
   - Benchmark raw `tesseract` (`nep+eng`) baseline first.
   - Implement and benchmark lightweight preprocessing (300-DPI normalization for low-res inputs, grayscale + adaptive binarization/Otsu thresholding, border cleanup, deskew) behind `HAMIGENZ_OCR_PREPROCESS` (`1` default when proven, `0` instant fallback).
   - **Decision Gate:** Only if Tesseract + lightweight preprocessing cannot reach the target CER/WER on the locked corpus will a separate spike evaluate `PaddleOCR` (`devanagari_PP-OCRv5_mobile_rec`) against the dependency/resource budget.

#### Measurable Success Criteria (4A)
- Locked corpus contains >= 25 paired samples with 100% `MANIFEST.json` license and PII clearance.
- **>= 20% relative CER reduction** vs. raw `tesseract` baseline on the real-world corpus (target **<= 15.0% avg CER** and **<= 25.0% avg WER** on clean/moderate real public notices).
- **Zero regression** on the existing synthetic OCR benchmark (`tests/test_ocr_evaluation.py` thresholds) and **0 new heavyweight ML dependencies** added to `backend/requirements.txt` unless explicitly approved after benchmark evidence.
- Offline CI runtime remains < 5 min for `Backend CI`.

#### Test Strategy (4A)
- Deterministic `pytest tests/test_ocr_evaluation.py` covering both synthetic and real-world corpora offline.
- Unit tests for preprocessing transforms (deskew angle clamping, empty/corrupt image safety, NFC output normalization).

#### Rollback Criteria & Procedure (4A)
- **Trigger:** Any regression in synthetic OCR thresholds, median page latency > 2x baseline on CPU, or CI timeout/OOM.
- **Action:** Set `HAMIGENZ_OCR_PREPROCESS=0` (immediate runtime bypass) or revert the preprocessing helper commit; `IMPLEMENTED_ENGINES = ("tesseract",)` and existing API/storage contracts remain unchanged.

---

### Milestone 4B (Separately Scoped): OKF & Document Grounding Metrics + Citation Verification

#### Scope
1. **Gold Grounding Evaluation Set (`tests/evaluation/gold_grounding/`):**
   - Curate >= 25 deterministic test cases spanning `okf`-routed questions, `document`-routed questions (fees, deadlines, eligibility, Nepali numerals), and unanswerable negative cases (must abstain).
2. **Deterministic Citation & Fact Verification (`backend/official_answer.py`, `backend/main.py`):**
   - Verify every returned citation (`page_num` for `document`, `concept_ids` for `okf`) maps to an actual retrieved item in the active request context.
   - Cross-check extracted numeric amounts (NPR fees, day counts, dates) against retrieved evidence; downgrade/warn on ungrounded numeric claims instead of presenting them as verified.
   - Optionally evaluate lightweight lexical scoring (`rank_bm25`) within `document` chunk selection (strictly preserving OKF v0.2 concept routing for `okf` queries), gated by `HAMIGENZ_LEXICAL_AUGMENT`.

#### Measurable Success Criteria (4B)
| Metric | Target |
|---|---|
| **Citation Existence Rate** (cited `page_num` / `concept_id` present in retrieved context) | **100%** |
| **Excerpt Grounding Support Rate** (citation excerpt verified in retrieved chunk/OKF text) | **>= 95%** |
| **Ungrounded Numeric/Deadline Fabrication Rate** | **0%** on gold benchmark |
| **Negative Abstention Rate** (unanswerable questions abstain cleanly) | **100%** |
| **OKF Concept Traceability** (`okf`-routed answers include valid `concept_ids`) | **100%** |

#### Test Strategy (4B)
- Offline `pytest` suite with mocked `OllamaService` + real `okf_bundle.py` and FAISS index retrieval, plus opt-in live `qwen3:8b` run (`HAMIGENZ_LIVE_LLM_TESTS=1`).

#### Rollback Criteria & Procedure (4B)
- **Trigger:** False-positive abstentions on > 5% of answerable gold questions or schema breakage in `/ask`.
- **Action:** Toggle `HAMIGENZ_LEXICAL_AUGMENT=0` / additive verifier warning mode; `/ask` response schema remains backwards-compatible.

---

### Milestone 4C (Separately Scoped): Privacy, Prompt-Guard & Deployment Security Hardening

#### Scope
1. **Prompt-Guard Unicode & Injection Hardening (`backend/prompt_guard.py`):**
   - Strip Unicode bidirectional control characters (`\u202a-\u202e`, `\u2066-\u2069`) alongside zero-width characters, normalize NFC before pattern matching, and expand injection test coverage.
2. **Non-Root Storage & Deployment Readiness (`backend/main.py`, `scripts/test_docker_persistence.sh`):**
   - Add an explicit non-secret startup/health check verifying `UPLOAD_DIR` and `VECTORS_DIR` writability for UID `10001`.
   - Document and validate Railway persistent-volume ownership, `HAMIGENZ_SESSION_SECRET` production enforcement, `TRUSTED_PROXIES` CIDR configuration, and frontend CSP headers (`frontend/test/csp.test.ts`).

#### Measurable Success Criteria (4C)
- **100%** neutralization of bidi-smuggled and zero-width-obfuscated prompt-injection test cases.
- **100%** pass rate across `tests/test_security.py`, `tests/test_upload_ingress.py`, `frontend/test/csp.test.ts`, and `scripts/test_docker_persistence.sh` under default rate limits.
- Railway staging volume permissions verified via checklist before any external deployment is approved.

#### Rollback Criteria & Procedure (4C)
- **Trigger:** False-positive sanitization corrupting legitimate Nepali document text or startup check blocking valid dev environments.
- **Action:** Revert the specific regex/pattern rule in `prompt_guard.py` or scope the writability check to `HAMIGENZ_ENV=production` without data migration.

---

## 5. Approval Gate

- **Next Action:** Review this plan (`docs/m4_implementation_plan.md`) and confirm approval to begin **Milestone 4A** (Real-World Nepali OCR Corpus & Lightweight Preprocessing).
- No M4 code changes, deployments, or releases will occur before approval.
