# hamiGenZ — Security Notes

Status: development-phase hardening in progress. This file tracks what is
implemented vs. planned. It is not a compliance document.

## Threat model (development phase)

hamiGenZ processes untrusted documents (PDFs, images, OCR output) and
untrusted text through a local LLM. The primary assets are:

1. User documents and their extracted text/vectors
2. The local machine (backend runs on localhost)
3. Answer integrity (no fabricated certainty, clear provenance)

### Access control & session isolation (Phase 1 / Phase 1.1)
- **Signed anonymous sessions**: HMAC-SHA256 authenticated session tokens (`s_<uuid>.<timestamp>.<signature>`) with 24-hour validity window.
- **Dual session transport**: Token is returned via both a `hamigenz_session` cookie (`SameSite=Lax`, `Secure` in prod) and an `X-Session-Token` response header. The frontend stores the token in `sessionStorage` (tab-scoped, cleared on close). This dual transport handles same-origin cookie flows and cross-site split-hosting where third-party cookies may be blocked.
- **Token storage model**: `X-Session-Token` is JS-readable via `sessionStorage`. This is intentional — the session contains no personal data and is scoped to the browser tab. Tokens are never written to URLs, response bodies, or logs.
- **Session secret management**: Controlled via `HAMIGENZ_SESSION_SECRET`. In production environments (`HAMIGENZ_ENV=production`), missing or default secrets fail closed with a fatal startup error to prevent fallback to hard-coded values.
- **CSRF protection — corrected policy (Phase 1.1)**: Mutating requests (`POST`, `PUT`, `DELETE`, `PATCH`) with an `Origin` header not in the approved CORS list are blocked unconditionally, UNLESS the request carries a valid `X-Session-Token` header.
  - `X-Requested-With` alone is **not** a sufficient CSRF defense. An attacker can set it from a non-browser client without going through CORS preflight.
  - `X-Session-Token` is sufficient: forging it requires the attacker to already know the victim's session credential.
  - Requests with no `Origin` header (direct API calls, same-origin) are not subject to this check.
- **Backend-enforced document ownership**: All document-scoped endpoints strictly verify caller ownership. Unauthorized or cross-user requests return uniform `HTTP 404 Not Found` (never 403 or 401) to prevent ID enumeration. Full route matrix:
  - `GET /documents` — session-scoped listing
  - `GET /documents/{id}/viewer` — ownership 404
  - `GET /documents/{id}/page/{n}/image` — ownership 404
  - `GET /documents/{id}/search-text` — ownership 404
  - `POST /documents/{id}/form-fields` — ownership 404
  - `POST /documents/{id}/page/{n}/fill-image` — ownership 404
  - `DELETE /documents/{id}` — ownership 404 (document preserved on unauthorized attempt)
  - `POST /explain` with `doc_id` — ownership 404
  - `POST /actions` with `doc_id` — ownership 404
  - `POST /forms/detect` with `doc_id` — ownership 404
  - `POST /forms/explain-field` with `doc_id` — ownership 404
  - `POST /ask` with `doc_id` — ownership 404
- **Public document listing elimination**: `GET /documents` is strictly scoped to the active caller's verified `session_id`. Cross-user document catalogs are completely inaccessible.
- **Query & vector isolation**: When `POST /ask` is called without `doc_id`, vector similarity search is restricted to documents belonging to the authenticated session (`allowed_doc_ids`). Zero foreign evidence chunks can ever be returned.
- **Safe SQLite migration & legacy quarantine**: `MetadataStore` automatically migrates schema with WAL mode, adding `session_id` and indexing `(session_id, doc_id)`. Unowned legacy records are permanently assigned to `__quarantined_legacy__`.

### Proxy trust & rate limiting (Phase 1 / Phase 1.1)
- **Safe client-IP resolution**: Client IP is evaluated using Python's `ipaddress` module. Forwarded headers are strictly ignored unless the direct socket peer matches a trusted proxy address, and `X-Forwarded-For` is traversed right-to-left.
- **Dual-tier sliding-window rate limiting**:
  - *Session tier*: 3 uploads per session per 60 seconds (env: `RATE_LIMIT_UPLOAD_SESSION`, default `3/60`).
  - *IP abuse tier*: **15** uploads per IP per 60 seconds (env: `RATE_LIMIT_UPLOAD_IP`, default `15/60`). General AI and search limits are also enforced.
  - *Standards compliance*: Requests exceeding limits receive `HTTP 429 Too Many Requests` with an integer `Retry-After` header.
  - **Single-worker limitation**: The rate limiter is in-memory (`threading.Lock` + `defaultdict`) and is per-process. In a multi-process deployment, limits are per-worker, not global. For shared enforcement across workers, replace with a Redis/Memcached backend.

### Frontend security headers (Phase 1.1)
- Production security headers configured in [`frontend/next.config.ts`](../frontend/next.config.ts):
  - **`Content-Security-Policy`**:
    - `'unsafe-eval'` **removed** (Phase 1.1 correction). Production Next.js builds do not use `eval()`.
    - `'unsafe-inline'` in `script-src` retained: Next.js injects inline chunk-bootstrapping scripts. Removing it requires a per-request nonce strategy (future hardening).
    - `connect-src` is **explicit**: constructed from `NEXT_PUBLIC_API_BASE_URL` at build time. The broad `https:` wildcard from Phase 1 is removed.
    - `base-uri 'self'` and `form-action 'self'` directives added.
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()`
  - **HSTS**: Not emitted by Next.js. Must be set at the reverse proxy/CDN layer. Vercel automatically applies HSTS for custom domains on Pro/Team plans.

### Upload / file handling
- Size limits: min 100 B, max 50 MB
- Extension allowlist: `.pdf .png .jpg .jpeg .tiff .tif`
- **Content-based validation**: declared MIME type and extension are ignored;
  magic bytes must match (`%PDF-`, `\x89PNG`, `\xff\xd8\xff`, TIFF II/MM)
- **Filename neutralization**: user filenames never touch the filesystem;
  files are saved as `<uuid>.<sanitized-ext>`; the resolved path must stay
  inside the upload directory
- Malformed documents return a clean 400 (no stack traces to the client);
  failed uploads are deleted
- Page-count limit (200) with rollback of vectors/metadata/file

### Path safety
- Document routes (viewer / page image / search / delete) verify the stored
  filepath resolves inside `UPLOAD_DIR` (defense against metadata tampering)
- Page numbers are bounds-checked before rendering
- `doc_id` is validated against metadata before vector retrieval

### CORS / API surface
- Explicit CORS origin allowlist (no wildcard + credentials);
  `FRONTEND_ORIGIN` + optional `CORS_EXTRA_ORIGINS` env config
- Exposed headers include `X-Session-Token` and `Retry-After`
- LLM backend failures map to a clean 503 with a user-friendly message

### Tests & Verification
- Phase 1 security regression suite (`tests/test_phase1_security.py`): 14/14 passing tests covering session lifecycle, token tampering, token expiry, cross-user isolation, vector query isolation, 3/session/min upload rate limiting with Retry-After, proxy boundary validation, CSRF defense (including X-Requested-With bypass fix), and legacy data quarantine.
- Phase 1.1 correction suite (`tests/test_phase1_1_corrections.py`): 63/63 passing tests covering CSP policy verification, corrected CSRF policy, session token lifecycle, rate-limit constant verification (IP ceiling=15), and full route authorization matrix (27 endpoint/session-pair combinations).
- Headless browser verification via Playwright (`scratch/browser_session_verification.py`): Two distinct browser sessions verify cookie issuance, document upload, cross-session 404 rejection, empty document enumeration, and clean document deletion.
- Existing unit tests (`tests/test_security.py`, `backend/tests/test_rate_limiter.py`): all passing.
- Frontend demo mode verification (`frontend/test/demo-mode.test.ts`): passing with 0 network calls.
- Next.js production build (`next build`): Completed cleanly with corrected CSP headers active.

## Planned (Phase 2 & beyond)

- CSP nonce strategy: thread a per-request nonce through Next.js middleware to allow removal of `'unsafe-inline'` from `script-src`
- Concurrency limits and processing timeouts for OCR/embedding jobs
- Prompt-injection hardening: documents are DATA, never instructions;
  deliberate adversarial-document tests
- Background TTL document and session cleanup task for ephemeral uploads
- Optional account-based authentication if long-lived persistent accounts are introduced (Argon2id password hashing, brute-force throttling)
- Shared rate limiter backend (Redis/Memcached) for multi-worker deployments
- Dependency audit (npm audit / pip-audit) as a pre-release gate
- HTTPS everywhere in production deployment

## Reporting

This is a local-first project without a bug bounty. If you find a security
issue, please open a minimal-issue report at the repository tracker without
posting exploit details publicly.
