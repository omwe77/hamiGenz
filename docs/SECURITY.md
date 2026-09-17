# hamiGenZ — Security Notes

Status: development-phase hardening in progress. This file tracks what is
implemented vs. planned. It is not a compliance document.

## Threat model (development phase)

hamiGenZ processes untrusted documents (PDFs, images, OCR output) and
untrusted text through a local LLM. The primary assets are:

1. User documents and their extracted text/vectors
2. The local machine (backend runs on localhost)
3. Answer integrity (no fabricated certainty, clear provenance)

## Implemented

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
- LLM backend failures map to a clean 503 with a user-friendly message

### Tests
- Test pipeline teardown runs in an isolated temp dir (previously walked
  and deleted the shared `data/` directory)
- Live-server verification: MIME spoof → 400, traversal filename
  neutralized, malformed PDF → 400, CORS headers sane

## Planned (before any public deployment)

- Rate limiting on expensive endpoints (`/ask`, `/explain`, `/upload`,
  search) — free/local solution first
- Concurrency limits and processing timeouts for OCR/embedding jobs
- Prompt-injection hardening: documents are DATA, never instructions;
  deliberate adversarial-document tests
- Security headers (CSP, X-Content-Type-Options, Referrer-Policy) at the
  serving layer
- Authentication + per-user document isolation (when accounts are
  introduced): Argon2id password hashing, brute-force throttling, generic
  auth errors, session fixation/theft protection, CSRF for cookie auth
- Privacy: explicit retention/deletion behavior for documents, extracted
  text, and vectors (deletion currently removes file + vectors + metadata)
- Dependency audit (npm audit / pip-audit) as a pre-release gate
- HTTPS everywhere in production; dev localhost stays HTTP

## Reporting

This is a local-first project without a bug bounty. If you find a security
issue, please open a minimal-issue report at the repository tracker without
posting exploit details publicly.
