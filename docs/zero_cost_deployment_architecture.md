# hamiGenZ — $0 Deployment Architecture Audit & Recommendation

**Revision 5 (Final Approved Baseline) — 2026-11-27**
**Status:** Architecture approved with final corrections — committed to `main` prior to implementation.

---

## Fact Labels

| Label | Meaning |
|---|---|
| `[VERIFIED]` | Confirmed from official provider documentation or direct inspection of the repository |
| `[ESTIMATE]` | Reasoned from published specs/pricing or architectural analysis, not directly benchmarked |
| `[UNTESTED ASSUMPTION]` | Plausible but not empirically tested in this audit — must be validated before production reliance |

---

## Executive Summary

1. **Remove Gemini Free from public production AI:** Under Gemini API's March 23, 2026 terms, unpaid-tier prompts and outputs (outside EEA/UK/CH) are used for model training and human review, personal information is prohibited, and under-18 consumer access is restricted. **Gemini Free is removed from public production** and retained **only as an optional internal development/testing provider** using synthetic data.
2. **Public Production AI Providers ($0, ZDR-verified, Cross-Family):**
   - **Primary Document Answer & General Q&A:** **Groq Free Tier** (`openai/gpt-oss-120b`) with **ZDR explicitly enabled and verified**.
   - **Independent Cross-Family Evaluator:** **Cloudflare Workers AI Free Tier** (`@cf/qwen/qwen3.8-27b`, ZDR by default) — chosen over `@cf/openai/gpt-oss-20b` to eliminate the **GPT-OSS shared-family limitation**, with `@cf/openai/gpt-oss-20b` as secondary Cloudflare fallback if Neuron burn or JSON compliance requires it.
   - **Local / Offline Development:** **Ollama (`Qwen3:8B`)** — zero external data exposure.
3. **Strict Token Budgets, Quota Handling & Unverified-Answer States:** Hard per-request token caps (`≤ 3,200` tokens on Groq generator; `≤ 2,350` tokens on Cloudflare evaluator), SQLite response caching, graceful **HTTP 429** handling, and explicit **`verified` / `unverified_evaluator_unavailable` / `unverified_flagged` / `rate_limited`** UI/API states.
4. **Age Gate & ZDR Pre-Flight Gate:** Both Groq (Services Agreement) and Gemini require users to be **18+**. Public Groq-backed AI features require an explicit 18+ age-gate/terms check (or restriction of un-gated minor traffic to deterministic OKF/OCR/local modes). **ZDR must be enabled and verified** before processing any user content.
5. **Frontend, Backend & Storage:** Keep **Vercel Hobby** (AI training opted out; uploads & Q&A bypass Vercel via direct `NEXT_PUBLIC_API_BASE_URL`), **Oracle Always Free (2 OCPU / 12 GB RAM / 200 GB combined)** if card/capacity succeed (else Fly.io / local), **SQLite WAL**, **FAISS**, **Tesseract (default OCR)**, and **OKF v0.2**.

---

## 1. Current Architecture Audit (`main` @ `a4056ef`)

| Layer | Verified Implementation |
|---|---|
| **Frontend** | Next.js 16.3.5 App Router (`frontend/src/app/workspace/[docId]/page.tsx` is a server component calling `getDocumentViewer(docId)` at request time; `generateStaticParams()` only pre-renders `demo-registration-form`). `frontend/next.config.ts` uses `async headers()` for CSP — **incompatible with static export (`output: 'export'`)**. `[VERIFIED]` |
| **API Routing (Frontend → Backend)** | `frontend/src/lib/hamigenz-api.ts` uses `NEXT_PUBLIC_API_BASE_URL` directly via browser `apiFetch()` (`credentials: "include"`, `X-Session-Token`). No Next.js `app/api/` proxy routes exist. `[VERIFIED]` |
| **Backend** | FastAPI + Uvicorn in `python:3.11-slim-bookworm`, non-root `UID 10001:10001`, port 8000. ARM64 Docker build validated on `ubuntu-24.04-arm` (`.github/workflows/arm64-validation.yml`). `[VERIFIED]` |
| **OCR & Embeddings** | `tesseract-ocr-eng` + `tesseract-ocr-nep` (default OCR), CPU-only `torch==2.15.0+cpu`, `sentence-transformers==3.1.1` (MiniLM-L12-v2, ~470 MB HF cache), `faiss-cpu==1.11.0`. `[VERIFIED]` |
| **Storage & Knowledge Base** | SQLite WAL (`hamigenz.db`, `feedback.db`), FAISS (`backend/data/vectors/`), local uploads (`backend/data/uploads/`), OKF v0.2 (`data/okf/`, 11 concept Markdown files). Zero PostgreSQL. `[VERIFIED]` |
| **LLM Wiring** | `GeminiService` in `backend/llm_service.py` (`store=False` in `interactions.create()`), switched via `LLM_PROVIDER`. Only one `app.state.llm` slot exists; no second independent evaluator is wired yet. `[VERIFIED]` |
| **Auth & Retention** | HMAC-SHA256 anonymous sessions; `SESSION_TTL_SECONDS = 86400` controls **session token expiry only**. There is **no automatic deletion** of `uploads/`, `vectors/`, or SQLite document rows when a session expires (known gap). `[VERIFIED]` |

---

## 2. Gemini Free Tier Removal & Age Restrictions

### 2.1 Gemini Free Tier (Removed from Public Production)
Under the **Gemini API Additional Terms of Service** (updated **March 23, 2026**): `[VERIFIED]`
- **Unpaid-tier data use:** Outside the EEA, Switzerland, and the UK, Google uses prompts, inputs, and outputs from unpaid services to improve and train its products, including automated and human review.
- **`store=False` is not a training exemption:** `store=False` only disables conversation history storage; it does not override unpaid-tier training terms. `[ESTIMATE]`
- **Personal information prohibited:** Google explicitly instructs developers not to submit sensitive, confidential, or personal information to unpaid services. A UI consent banner does not cure a developer-side terms violation.
- **Under-18 restriction:** Standard Gemini API terms prohibit building apps directed at or likely accessed by users under 18.
- **Decision:** **Removed from public production.** Retained strictly for internal developer testing (`LLM_PROVIDER=gemini`) using synthetic data only.

### 2.2 Groq Age Requirements & Minors Responsibility
Under the **Groq Services Agreement ("Age Requirement")**: `[VERIFIED]`
> *"You must be 18 years of age or older to access or use the Cloud Services. By using the Cloud Services, you represent that you are age 18 or older. If you are not 18 or older, you may not access or use the Cloud Services."*

- **Operational Responsibility:** Because hamiGenZ targets civic-tech / youth ("GenZ") audiences who may include minors under 18:
  1. **Public Groq-backed AI routes** must be gated behind an explicit **18+ age-confirmation / terms-acceptance check** before invoking Groq Cloud Services.
  2. Users who do not confirm 18+ (or un-gated public demo modes) must be routed only to **deterministic OKF v0.2 / OCR / local-Ollama** paths, never to Groq Cloud APIs.
  3. Operators must not knowingly allow under-18 access to Groq-backed inference.

---

## 3. Groq Free Plan vs. Developer Plan (Verified Limits)

Groq's official rate-limit documentation (`console.groq.com/docs/rate-limits`) separates the **Free** plan (no card) from the pay-as-you-go **Developer** plan (card required): `[VERIFIED]`

| Plan | Model | RPM | RPD | TPM | TPD | Billing / Card |
|---|---|---|---|---|---|---|
| **Free Plan** | `openai/gpt-oss-120b` | **30** | **1,000** | **8,000** | **200,000** | $0, no card required |
| **Free Plan** | `openai/gpt-oss-20b` | **30** | **1,000** | **8,000** | **200,000** | $0, no card required |
| **Free Plan** | `qwen/qwen3.8-27b` | **30** | **1,000** | **8,000** | **200,000** | $0, no card required |
| **Developer Plan** | `openai/gpt-oss-120b` / `20b` | 1,000 | Scaled | 250,000 | Scaled | Pay-as-you-go (card required) |

- Free-plan limits are **organization-wide shared** across API keys.
- **Groq ZDR (Zero Data Retention):** Available on **all tiers including Free**, **off by default** (default = temporary logging up to 30 days for error/abuse in US GCP buckets; Groq does not train on customer data on any tier). **ZDR must be explicitly enabled and verified** in Groq Console → Settings → Data Controls before processing any user content. `[VERIFIED]`

---

## 4. Independent Evaluator Assessment: GPT-OSS Shared-Family Limitation & Cloudflare `qwen3.8-27b`

### 4.1 The GPT-OSS Shared-Family Limitation
Using **Groq `openai/gpt-oss-120b`** as the generator and **Cloudflare `@cf/openai/gpt-oss-20b`** as the evaluator provides *provider* diversity (Groq vs. Cloudflare) but **not *model-family* diversity**:
- Both models originate from the same OpenAI `gpt-oss` open-weight family and share similar pretraining distributions, RLHF/reasoning priors, and tokenization biases. `[ESTIMATE]`
- **Risk:** Correlated blind spots — if `gpt-oss-120b` hallucinates a plausible-sounding Nepali civic rule or misinterprets a Devanagari OCR artifact, a smaller `gpt-oss-20b` from the same family is more likely to agree with that phrasing than an unrelated model family.

### 4.2 Three-Way Evaluator Comparison

| Dimension | Groq (`openai/gpt-oss-120b`) | Cloudflare (`@cf/openai/gpt-oss-20b`) | Cloudflare (`@cf/qwen/qwen3.8-27b`) |
|---|---|---|---|
| **Model-Family Independence** | ❌ Same family as generator (`gpt-oss`) | ❌ Same family as generator (`gpt-oss`) | ✅ **Cross-family** (Qwen vs. OpenAI GPT-OSS) `[VERIFIED]` |
| **Cost & Billing Risk** | **$0** (Free plan, no card, 429 on cap) `[VERIFIED]` | **$0** (10,000 Neurons/day hard stop on Free plan) `[VERIFIED]` | **$0** (10,000 Neurons/day hard stop on Free plan) `[VERIFIED]` |
| **Actual Free Quota** | **1,000 RPD / 30 RPM / 8,000 TPM / 200,000 TPD** (shared with generator!) `[VERIFIED]` | **10,000 Neurons/day** (~18.2k Neurons/1M in, ~27.3k/1M out → **~146–314 evals/day**) `[VERIFIED pricing / ESTIMATE capacity]` | **10,000 Neurons/day** (262,144 context window; exact per-1M-token Neuron rate not separately published beyond $0.011/1k Neurons base — must measure in staging) `[VERIFIED model / ESTIMATE capacity]` |
| **Nepali Quality** | Expected strong (120B MoE) `[UNTESTED ASSUMPTION]` | Expected weaker (20B MoE) `[UNTESTED ASSUMPTION]` | Expected stronger multilingual/South-Asian script handling than 20B peer (27B) `[UNTESTED ASSUMPTION]` |
| **JSON Compliance** | ✅ Strict `json_schema` `[VERIFIED]` | ✅ OpenAI-compatible `response_format` (`json_object` / `json_schema`) `[VERIFIED]` | OpenAI-compatible Workers AI endpoint; JSON compliance must be verified in staging `[UNTESTED ASSUMPTION]` |
| **Latency** | ~500 tps (Groq LPU) `[VERIFIED]` | Distributed edge GPU (slower than LPU) `[VERIFIED]` | Distributed edge GPU (slower than LPU) `[ESTIMATE]` |
| **Privacy & ZDR** | Opt-in ZDR on Free (must enable; default 30-day logs) `[VERIFIED]` | **ZDR by default** (no storage/training if AI Gateway logging OFF) `[VERIFIED]` | **ZDR by default** (no storage/training if AI Gateway logging OFF) `[VERIFIED]` |

### 4.3 Evaluator Decision
- **Primary Independent Evaluator Candidate:** **Cloudflare Workers AI (`@cf/qwen/qwen3.8-27b`)** — provides **true cross-family independence** from `openai/gpt-oss-120b`, **ZDR by default**, and a **separate 10,000 Neurons/day free quota** that does not consume Groq's 8,000 TPM / 200,000 TPD generator budget.
- **Secondary Fallback Candidate:** **Cloudflare Workers AI (`@cf/openai/gpt-oss-20b`)** — if staging tests show `@cf/qwen/qwen3.8-27b` consumes excessive Neurons per evaluation or fails strict JSON schema adherence, fall back to `@cf/openai/gpt-oss-20b` (documenting the shared-family caveat).

---

## 5. Strict Token Budgets, Quota Handling, HTTP 429 Behaviour & Verification States

### 5.1 Strict Per-Request Token Budgets
To operate sustainably inside Groq Free (**8,000 TPM / 200,000 TPD**) and Cloudflare Free (**10,000 Neurons/day**):
- **Generator (`openai/gpt-oss-120b` on Groq Free):**
  - `max_input_tokens`: **≤ 2,500** (system prompt + OKF v0.2 concept + top-k OCR chunks; truncate/reject oversized context before calling Groq)
  - `max_output_tokens`: **≤ 700**
  - **Total budget:** **≤ 3,200 tokens/call** → supports ~2–3 calls/min within 8,000 TPM and **≥ 62 full Q&A calls/day** within 200,000 TPD (more with smaller prompts).
- **Evaluator (`@cf/qwen/qwen3.8-27b` / `@cf/openai/gpt-oss-20b` on Cloudflare Free):**
  - `max_input_tokens`: **≤ 2,000** (user question + retrieved evidence + generator answer)
  - `max_output_tokens`: **≤ 350** (strict JSON: `{verdict, score, grounded, issues}`)
  - **Total budget:** **≤ 2,350 tokens/call**.

### 5.2 Quota Handling & HTTP 429 Behaviour
1. **Response & Evaluation Caching:** Cache `(doc_hash, normalized_question, provider_model)` answers and evaluation verdicts in SQLite so repeated queries never consume upstream quota.
2. **Pre-Call Local Rate Limiter:** Enforce per-session request throttling in FastAPI before hitting Groq/Cloudflare.
3. **Upstream HTTP 429 / Quota Exhaustion Behaviour:**
   - **Never** retry 429s in an unbounded loop and **never** silently return unverified/fabricated answers.
   - If the **Generator (Groq)** returns HTTP 429 or hits daily budget: return **HTTP 429** (forwarding `Retry-After` if present) OR a structured `rate_limited` response with deterministic OKF v0.2 concept + OCR snippet fallback and an explicit banner: *"Live AI answer quota reached. Showing verified OKF/OCR excerpts only."*
   - If the **Evaluator (Cloudflare)** returns HTTP 429, times out, or produces invalid JSON: **do not fail-open as verified**. Return the generator's answer tagged with `verification_status: "unverified_evaluator_unavailable"`.

### 5.3 Explicit Answer Verification States (API & UI Contract)
Every AI response must include an explicit `verification_status` enum:
- `verified`: Generator succeeded AND independent cross-family evaluator returned valid structured JSON passing grounding checks.
- `unverified_evaluator_unavailable`: Generator succeeded, but evaluator hit HTTP 429, timeout, or schema failure. UI must display a clear **"Unverified — Independent Check Unavailable"** badge.
- `unverified_flagged`: Evaluator returned valid JSON flagging unsupported claims or contradictions. UI must display **"Flagged — Review Source Document"** and highlight the discrepancy.
- `rate_limited`: Generator quota exhausted (HTTP 429). UI shows deterministic OKF/OCR excerpts only.

---

## 6. Vercel Hobby Terms & Direct Backend Bypass

- **Non-commercial restriction:** Vercel Hobby is strictly for personal/non-commercial use; hard caps apply (100 GB bandwidth, 1M edge requests, 1M function invocations, 4 CPU-hours/month) with no overage billing. `[VERIFIED]`
- **Default AI training opt-in:** Hobby plans are opted in by default for Vercel to use hosted "Your Content" (code, build telemetry, Vercel agent chats) for AI training. **Action:** Toggle **Opt-Out** in Vercel Dashboard → Team Settings → Data Preferences. `[VERIFIED]`
- **Direct Upload & Q&A Bypass:** Verified in `frontend/src/lib/hamigenz-api.ts` and `frontend/next.config.ts`: all document uploads, OCR/viewer calls, and questions go directly from the browser to `NEXT_PUBLIC_API_BASE_URL` over HTTPS. No Next.js `app/api/` proxy routes exist. Citizen documents never touch Vercel servers. `[VERIFIED]`

---

## 7. Pre-Flight ZDR Verification Gate

Before any real user content is processed in public production:
1. **Groq ZDR:** Log in to Groq Console → Settings → Data Controls → **Enable ZDR**, verify status shows active, and record verification evidence.
2. **Cloudflare Workers AI ZDR:** Confirm AI Gateway logging/caching is **disabled** and no R2/KV prompt-logging bindings are attached.
3. **Runtime Config Guard:** Backend startup must require explicit `ZDR_VERIFIED=true` before enabling public external AI routes (`GROQ_API_KEY` / `CLOUDFLARE_AI_TOKEN`), failing closed to deterministic/local mode if unset.

---

## 8. Final Recommended $0 Architecture & Explicit Limitations

```
[User Browser] (18+ gate for public cloud AI)
   ├──(Static/SSR Shell only)──► [Vercel Hobby] (AI Training Opt-Out ON)
   └──(All Uploads, Q&A, Sessions — direct HTTPS via NEXT_PUBLIC_API_BASE_URL)──►
                                  [FastAPI Backend (Docker ARM64)]
                                  Host: Oracle Always Free (2 OCPU / 12 GB RAM / 200 GB)
                                  Fallback: Fly.io (RAM-constrained) / Local Ollama
                                  Storage: SQLite WAL + FAISS + uploads/ + OKF v0.2
                                       │
                                       ├── Primary Answer & General Q&A:
                                       │     Groq Free (`openai/gpt-oss-120b`, ZDR ON, ≤3,200 tok/call)
                                       ├── Independent Cross-Family Evaluator:
                                       │     Cloudflare Workers AI (`@cf/qwen/qwen3.8-27b`, ZDR, ≤2,350 tok/call)
                                       │     (Fallback: `@cf/openai/gpt-oss-20b`)
                                       └── Internal Dev / Synthetic Only:
                                             Ollama (`Qwen3:8B`) or Gemini Free (synthetic data only)
```

### Explicit Limitations (What Cannot Be Achieved for $0)
1. **No Gemini in public production** (March 23, 2026 unpaid-tier training, PII, and under-18 terms).
2. **Strict daily AI ceilings:** Groq Free (8,000 TPM / 200,000 TPD) and Cloudflare Free (10,000 Neurons/day) cap burst concurrency and daily evaluations.
3. **Untested Nepali & JSON benchmarks:** `@cf/qwen/qwen3.8-27b`, `@cf/openai/gpt-oss-20b`, and `openai/gpt-oss-120b` must be benchmarked on Nepali civic documents and Neuron burn before production sign-off.
4. **Minors cannot use Groq-backed routes:** Enforced by Groq Services Agreement (18+ only).
5. **Oracle card & idle-reclamation risk:** Card signup may fail in Nepal; Always Free VMs with <20% 95th-percentile CPU, network, AND memory over 7 days can be reclaimed.
6. **Document retention gap:** `SESSION_TTL_SECONDS = 86400` expires auth tokens only; automatic cleanup of `uploads/`, `vectors/`, and SQLite rows is not yet implemented and is required before any real-document pilot.
7. **No 99.9% SLA or auto-scaling:** Single-VM deployment without managed backups.
