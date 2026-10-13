# Reference-Filled Form Preview (hamigenz)

Reference implementation: form fields are detected on an uploaded PDF/page, the
user types answers, and a PNG is returned with each answer composited onto its
correct field on the original page image.

## Done

- `backend/form_preview.py`: Pillow compositing of answers onto the original
  page image (200 DPI for display, 300 DPI for the preview) with a
  Devanagari-capable font (`Nirmala.ttc`).
- `backend/form_understanding.py`: field-position detection (Tesseract TSV at
  300 DPI) returning `x/y/w/h` per field.
- `backend/document_processor.py`: `MetadataStore.set_form_fields`/
  `get_form_fields`; `_render_page_pil(dpi)`; fixed conf int/str handling in
  word-boxes.
- `backend/main.py`: `POST /documents/{doc_id}/page/{page_num}/fill-image`
  (composites answers onto the correct fields, returns PNG), `POST
  /documents/{doc_id}/form-fields` (persist field values), page-existence 404
  check, and out-of-upload-dir path guard 403.
- `frontend/src/components/workspace/WorkspacePage.tsx`: doc-list "Open" button
  now `router.push(\`/workspace/${doc.doc_id}\`)`, so switching documents
  navigates to the correct per-doc URL.
- `frontend/src/app/workspace/[docId]/page.tsx`: server-rendered per-document
  home page; `DocViewerClient.tsx` client wrapper.
- `frontend/next.config.ts`: `output: "export"` -> `"standalone"` (dynamic routes
  are required for per-doc URLs).
- Tests: end-to-end fill-image flow (status codes, PNG bytes, empty values), and
  field-position + compositing unit checks.

## Still left

- Frontend field-editor/overlay UI wired to the fill panel (list + preview not
  yet connected in the workspace UI).
- Per-document routing review: decide whether `/workspace/<docId>` routes are
  needed, and confirm `output: "standalone"` is correct for the intended free
  Next.js hosting (SSR for auth-required docs is not yet exercised).
- Backend tests: field alignment, missing values, multipage documents, and
  failure handling to be covered by a committed `tests/` suite.
- Production build verification + deployment plan (Next.js + FastAPI) with
  storage limits and required env vars.
- Ollama-free path reviewed (fill-image does not call the LLM).
