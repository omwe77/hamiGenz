# Reference-Filled Form Preview (hamigenz)

Reference implementation: form fields are detected on an uploaded PDF/page, the
user types answers, and a PNG is returned with each answer composited onto its
correct field on the original page image.

## Done

- `backend/form_preview.py`: Pillow compositing of answers onto the original
  page image (200 DPI for display, 300 DPI for the preview) with a
  Devanagari-capable font (`Nirmala.ttc`), per-size font caching, and PyMuPDF `fitz` import.
- `backend/form_understanding.py`: field-position detection (Tesseract TSV at
  300 DPI) returning `x/y/w/h` per field.
- `backend/document_processor.py`: `MetadataStore.set_form_fields`/
  `get_form_fields`; `_render_page_pil(dpi)`; fixed conf int/str handling in
  word-boxes.
- `backend/main.py`: `POST /documents/{doc_id}/page/{page_num}/fill-image`
  (composites answers onto the correct fields, returns PNG), `POST
  /documents/{doc_id}/form-fields` (persist field values), page-existence 404
  check, and out-of-upload-dir path guard 403.
- `frontend/src/components/workspace/FillPanel.tsx`: Reference preview panel with
  asynchronous canvas compositing (`renderPreviewCanvas`), field value editors,
  stale-render sequence tracking (`renderSeqRef`), and direct client-side PNG download.
- `frontend/src/components/workspace/WorkspacePage.tsx`: Top-bar demo/live toggle
  with API synchronization (`setDemoModeState`), per-document workspace routing.
- `frontend/public/blank_form.png`: 800×600 clean blank registration form fixture
  for the interactive demo preview.
- `backend/tests/`: Unit test suite (`test_form_preview.py`, `test_action_extractor.py`,
  `test_okf_validator.py`) with 26 passing tests covering font caching, field bounds,
  Devanagari digits, and OKF v0.2 frontmatter validation.
- `frontend/`: Clean TypeScript build (`npm run build`) passing with Turbopack.

## Verification Checklist

- [x] Asynchronous canvas drawing with image load await
- [x] Stale render sequence counter in FillPanel
- [x] Safe toggleDemoMode event handler
- [x] Valid non-empty PNG download
- [x] Backend tests hermetic with stubs
- [x] Standard ESLint config restored
