# hamiGenZ — Security Notes

Status: development-phase hardening in progress. This file tracks what is
implemented vs. planned. It is not a compliance document.

> [!WARNING]
> **Not Ready for Public Traffic**: The backend is hardened for local development,
> evaluation, and isolated testing. It is NOT approved or configured for public Internet
> traffic or production exposure. Public deployment requires production secret provisioning,
> reverse-proxy TLS termination with HSTS, an external shared rate limiter (e.g. Redis),
> and Phase 2 data lifecycle controls.

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
- **Session secret management**: Canonical configuration via `HAMIGENZ_SESSION_SECRET` and `HAMIGENZ_ENV`. In production mode (`HAMIGENZ_ENV=production`), `HAMIGENZ_SESSION_SECRET` is strictly required and must be generated using a cryptographically secure method (e.g. `python -c "import secrets; print(secrets.token_hex(32))"`). Startup validation enforces a minimum of 32 characters and rejects obvious weak patterns (including known placeholder names, single-character repetitions such as `"a" * 32`, simple repeating chunks, and sequential characters), failing closed with a fatal error (`RuntimeError` / `ValueError`). Note that heuristic validation serves solely as a defense-in-depth safety guard against placeholder misconfigurations and does not prove that an arbitrary secret has sufficient entropy. Legacy `SESSION_SECRET` is intentionally ignored in production to prevent misconfiguration or accidental fallback. In non-production, an unconfigured secret generates a secure per-instance 32-byte random key.
- **CSRF protection — corrected policy (Phase 1.1)**: Mutating requests (`POST`, `PUT`, `DELETE`, `PATCH`) with an `Origin` header not in the approved CORS list are blocked unconditionally (HTTP 403), UNLESS the request carries a cryptographically verified `X-Session-Token` header.
  - `X-Requested-With` alone is **not** a sufficient CSRF defense and is blocked from unapproved origins.
  - Merely providing an arbitrary or invalid `X-Session-Token` header is blocked; the token must pass HMAC signature verification and timestamp expiration checks.
  - Requests with no `Origin` header (direct API calls, same-origin) are not subject to this check.
- **Backend-enforced document ownership**: All document-scoped endpoints strictly verify caller ownership. Unauthorized or cross-user requests return uniform `HTTP 404 Not Found` (never 403 or 401) to prevent ID enumeration. Every document-scoped endpoint is tested across the complete triad: Owner (200), Non-owner (404), and Anonymous (404):
  - `GET /documents` — session-scoped listing (owner sees only own docs, non-owner/anonymous sees none)
  - `GET /documents/{id}/viewer` — owner 200, non-owner 404, anonymous 404
  - `GET /documents/{id}/page/{n}/image` — owner 200, non-owner 404, anonymous 404
  - `GET /documents/{id}/search-text` — owner 200, non-owner 404, anonymous 404
  - `POST /documents/{id}/form-fields` — owner 200, non-owner 404, anonymous 404
  - `POST /documents/{id}/page/{n}/fill-image` — owner 200, non-owner 404, anonymous 404
  - `DELETE /documents/{id}` — owner 200, non-owner 404 (document preserved), anonymous 404 (document preserved)
  - `POST /explain` with `doc_id` — owner 200, non-owner 404, anonymous 404
  - `POST /actions` with `doc_id` — owner 200, non-owner 404, anonymous 404
  - `POST /forms/detect` with `doc_id` — owner 200, non-owner 404, anonymous 404
  - `POST /forms/explain-field` with `doc_id` — owner 200, non-owner 404, anonymous 404
  - `POST /ask` with `doc_id` — owner 200, non-owner 404, anonymous 404
- **Public document listing elimination**: `GET /documents` is strictly scoped to the active caller's verified `session_id`. Cross-user document catalogs are completely inaccessible.
- **Query & vector isolation**: When `POST /ask` is called without `doc_id`, vector similarity search is restricted to documents belonging to the authenticated session (`allowed_doc_ids`). Zero foreign evidence chunks can ever be returned.
- **Safe SQLite migration & legacy quarantine**: `MetadataStore` automatically migrates schema with WAL mode, adding `session_id` and indexing `(session_id, doc_id)`. Unowned legacy records are permanently assigned to `__quarantined_legacy__`.

### Proxy trust & rate limiting (Phase 1 / Phase 1.1)
- **Safe client-IP resolution**: Client IP is evaluated using Python's `ipaddress` module against `TRUSTED_PROXIES` (default: loopback `127.0.0.1,::1`). Forwarded headers are strictly ignored unless the direct socket peer matches a trusted proxy address, and `X-Forwarded-For` is traversed right-to-left.
- **Dual-tier sliding-window rate limiting**:
  - *Session tier*: 3 uploads per session per 60 seconds (env: `RATE_LIMIT_UPLOAD_SESSION`, default `3/60`).
  - *IP abuse tier*: **15** uploads per IP per 60 seconds (env: `RATE_LIMIT_UPLOAD_IP`, default `15/60`). General AI and search limits are also enforced.
  - *Standards compliance*: Requests exceeding limits receive `HTTP 429 Too Many Requests` with an integer `Retry-After` header.
  - **Single-worker limitation**: The rate limiter is in-memory (`threading.Lock` + `defaultdict`) and is per-process. In a multi-process deployment, limits are per-worker, not global. For shared enforcement across workers, replace with a Redis/Memcached backend.

### Frontend security headers (Phase 1.1)
- Production security headers configured in [`frontend/next.config.ts`](../frontend/next.config.ts) using typed, least-privilege helper `buildCsp()`:
  - **`Content-Security-Policy`**:
    - `'unsafe-eval'` **strictly absent**. Production Next.js builds do not use `eval()`.
    - `'unsafe-inline'` in `script-src` retained: Next.js injects inline chunk-bootstrapping scripts. Removing it requires a per-request nonce strategy (future hardening).
    - `connect-src` **strictly least-privilege**:
      - Production without `NEXT_PUBLIC_API_BASE_URL`: strictly `connect-src 'self'` without localhost, loopback, or wildcard `ws:`/`wss:` sources.
      - Production with configured `NEXT_PUBLIC_API_BASE_URL`: validated via `new URL()` parser to extract explicit `parsed.origin` (scheme + host + port) only, rejecting paths or trailing parameters. In production, the protocol **must be `https:`**; plain `http:`, `javascript:`, `ftp:`, `data:`, or malformed URLs throw a fatal configuration error and fail closed. Results in `connect-src 'self' <origin>`.
      - Development mode: permits explicit local development origins (`http://localhost:8000 http://127.0.0.1:8000`), dev HTTP/HTTPS API URLs, and explicit HMR WebSocket connections (`ws://localhost:3000`, `ws://127.0.0.1:3000`, `wss://localhost:3000`, `wss://127.0.0.1:3000`). Broad wildcard `ws:` and `wss:` scheme sources are strictly eliminated.
    - `img-src` **least-privilege**:
      - Production: `'self' data: blob:` (plus validated API origin when configured). No broad `https:` wildcard or localhost fallbacks in production.
      - Development: includes local backend dev servers for preview rendering.
    - `base-uri 'self'`, `form-action 'self'`, and `frame-ancestors 'none'` directives enforced.
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
- Phase 1 security regression suite (`tests/test_phase1_security.py`): 14/14 passing tests covering session lifecycle, token tampering, token expiry, cross-user isolation, vector query isolation, 3/session/min upload rate limiting with Retry-After, proxy boundary validation, CSRF defense, and legacy data quarantine.
- Phase 1.1 correction suite (`tests/test_phase1_1_corrections.py`): 73/73 passing tests covering least-privilege CSP policy verification (including HTTPS enforcement and no broad WebSockets), corrected CSRF policy, session token lifecycle, subprocess-isolated production secret configuration (including canonical-only requirement and weak-pattern rejection), rate-limit constant verification (IP ceiling=15), and the complete 3-way route authorization matrix (Owner 200, Non-owner 404, Anonymous 404 across all document routes).
- Existing unit tests (`tests/test_security.py`, `backend/tests/test_rate_limiter.py`): 7/7 and 5/5 passing.
- Frontend test suite (`npm test`):
  - `frontend/test/demo-mode.test.ts`: 12/12 passing with 0 network calls.
  - `frontend/test/csp.test.ts`: 4/4 passing test suites verifying production no-API URL, production with API URL, malformed URL rejection, and development HMR configurations.
- Next.js production build (`next build`): Completed cleanly with CSP and security headers active.

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
