# hamigenz backend — Phase 1 MVP

## Architecture

```
User Upload (PDF/Image)
    → Text Extraction / OCR
    → Cleaning & Chunking
    → Embeddings (sentence-transformers)
    → FAISS Index
    → User Query
    → Retrieval (top-k chunks)
    → Ollama qwen3:8b
    → Grounding Validation
    → Answer + Citations
```

## API Endpoints (FastAPI)

- `POST /upload` — Upload document (PDF/PNG/JPG), returns doc_id
- `POST /ask` — Ask question about uploaded doc, returns answer + citations
- `POST /ask-general` — General Nepal query (no doc), uses KB + LLM
- `GET /documents` — List user's uploaded documents
- `DELETE /documents/{doc_id}` — Delete document + its vectors
- `GET /health` — Health check

## Core Components

### 1. Document Processor
- Detect file type (PDF vs image)
- Extract text:
  - PDF: pdfplumber (text-based) + fallback to pymupdf
  - Scanned/image: pytesseract OCR (Nepali + English langs)
- Clean text (remove excessive whitespace, normalize Unicode)
- Chunk into sections (by page + semantic boundaries)
- Store metadata: filename, upload_date, pages, language detected

### 2. Embedding Service
- Use sentence-transformers `all-MiniLM-L6-v2` (free, lightweight)
- Embed each chunk
- Store in FAISS index keyed by doc_id

### 3. Retrieval Service
- Embed user query
- Search FAISS for top-k relevant chunks
- Include page number / chunk index in metadata for citations
- Optional: simple reranking by cosine similarity threshold

### 4. LLM Service (Ollama)
- Send retrieved context + user question to qwen3:8b
- Prompt includes:
  - Role: helpful explainer for Nepali documents
  - Language detection / response language preference
  - Grounding instruction: only answer from provided context + cite pages
  - Simple explanation instruction
- Stream or block response

### 5. Grounding Validator
- Extract key claims from generated answer
- Check each claim against retrieved chunks
- Classify: Supported / Partially Supported / Contradicted / Insufficient Evidence
- Flag unsupported factual claims (fees, deadlines, penalties, legal statements)
- Attach confidence note to response

### 6. Explanation Engine
- Structure answer:
  - What is this?
  - What does it mean?
  - What do I need to do?
  - Important dates / fees / requirements (if extractable)
  - Source citations
- Detect if document appears to be a form → offer field explanation
- Simple language, minimize jargon

## Language Handling

- Detect input language (Nepali script, Romanized Nepali, English, mixed)
- Pass language hint to LLM
- Support response language preference (user can request English answer even if question in Nepali)
- Romanized Nepali examples the system should handle:
  - "passport banauna k k chainxa?"
  - "deadline kahile ho?"
  - "yo form kasailai hunxa?"

## File Storage

- Uploads stored in `data/uploads/{session_id}/{doc_id}.ext`
- Vectors in FAISS index files in `data/vectors/`
- Metadata in SQLite `data/hamigenz.db`
- Session isolation: each user session gets isolated doc namespace
- Deletion: remove files + FAISS entries + DB record

## Security (Phase 1 baseline)

- Treat uploads as untrusted
- No user docs added to public KB
- No training on uploads
- Prompt injection defense: sandboxed prompt construction, no raw user text injected into system instructions without sanitization
- Per-session isolation in DB and file storage

## Free-First Check

| Component | Choice | Cost |
|---|---|---|
| LLM | Ollama qwen3:8b | Free (local) |
| Embeddings | sentence-transformers | Free |
| Vector DB | FAISS | Free |
| OCR | Tesseract | Free |
| PDF | pdfplumber/pymupdf | Free |
| Backend | FastAPI | Free |
| Frontend | Next.js | Free |
| DB | SQLite | Free |
| Hosting | Local / free tier | Free |

## Test Document (Phase 1 prototype)

Before full UI, use a legitimate public Nepal government document as test.
Create 10-20 known Q&A pairs to validate:

- "Yo document ko purpose ke ho?"
- "Maile k k document submit garnu parcha?"
- "Deadline kahile ho?"
- "Yo requirement kaslai apply huncha?"
- "Page 3 ma ke bhaneko cha?"

Validate: Question → Retrieval → Answer → Citation → Grounding
