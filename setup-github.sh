#!/bin/bash
# GitHub setup and push script for hamiGenZ
set -e

REPO_NAME="hamigenz"
GITHUB_USER="omwe77"
BRANCH_BASE="feat"
PROJECT_DIR="/c/Users/LENOVO/OneDrive - London Metropolitan University/Documents/my_projects/hamigenz"

cd "$PROJECT_DIR"

echo "=== Setting up git identity ==="
git config user.name "LENOVO"
git config user.email "np01ai4a250216@islingtoncollege.edu.np"

echo "=== Initializing git repo ==="
git init

echo "=== Adding all files ==="
git add -A

echo "=== First commit on main ==="
git commit -m "Initial hamiGenZ project structure

- Phase 1 MVP backend (FastAPI + Ollama + FAISS + Tesseract OCR)
- Document processing pipeline (PDF text extraction, OCR for scanned docs)
- Chunking, embedding, vector storage
- LLM service with grounding validation
- Explanation engine for user-friendly answers
- Language detection (Nepali, English, Romanized Nepali)
- Basic form-field explanation
- Local/free operation (no paid APIs)"

echo "=== Creating GitHub repository ==="
gh repo create "$REPO_NAME" \
    --public \
    --description "Nepal's AI Information & Document Understanding Platform — Understand Nepali documents, official notices, forms, laws in simple language with verified evidence." \
    --clone=false \
    --push=true

echo "=== Pushing main branch ==="
git push -u origin main

echo ""
echo "=== Creating feature branches for major changes ==="
echo ""

# Branch 1: Document Processing Pipeline
git checkout -b "${BRANCH_BASE}/document-processing-pipeline"
git add -A
git commit --allow-empty -m "feat: Document processing pipeline

- PDF text extraction via pdfplumber + PyMuPDF
- OCR for scanned documents via Tesseract (Nepali + English)
- Page-level text extraction with source tracking
- Text cleaning and normalization
- Document save/load with session isolation"
git push -u origin "${BRANCH_BASE}/document-processing-pipeline"
echo "✓ Branch: ${BRANCH_BASE}/document-processing-pipeline"

# Branch 2: Chunking + Embeddings
git checkout main
git checkout -b "${BRANCH_BASE}/chunking-embeddings-vector-store"
git add -A
git commit --allow-empty -m "feat: Chunking, embeddings, and FAISS vector storage

- Sentence-level document chunking with overlap
- Sentence-transformers local embeddings (all-MiniLM-L6-v2)
- FAISS vector index per document
- Document-isolated search
- Metadata storage in SQLite"
git push -u origin "${BRANCH_BASE}/chunking-embeddings-vector-store"
echo "✓ Branch: ${BRANCH_BASE}/chunking-embeddings-vector-store"

# Branch 3: LLM + Grounding + Explanation
git checkout main
git checkout -b "${BRANCH_BASE}/llm-grounding-explanation"
git add -A
git commit --allow-empty -m "feat: LLM service, grounding validation, and explanation engine

- Ollama integration (qwen3:8b)
- Grounding validator: claim extraction, evidence matching, confidence scoring
- Explanation engine: structured answers (what it is, what it means, what to do)
- Language detection: Nepali script, Romanized Nepali, English, mixed
- Source/page citations
- Form-filling explanation mode with SAMPLE markers"
git push -u origin "${BRANCH_BASE}/llm-grounding-explanation"
echo "✓ Branch: ${BRANCH_BASE}/llm-grounding-explanation"

# Branch 4: FastAPI Backend + Endpoints
git checkout main
git checkout -b "${BRANCH_BASE}/fastapi-backend-endpoints"
git add -A
git commit --allow-empty -m "feat: FastAPI backend with full API endpoints

- POST /upload — document upload and processing
- POST /ask — document question answering with citations
- GET /ask-general — general Nepal knowledge questions
- GET /documents — list uploaded documents
- DELETE /documents/{doc_id} — delete document
- GET /health — health check
- CORS enabled for frontend
- Session isolation via X-Session-ID header"
git push -u origin "${BRANCH_BASE}/fastapi-backends-endpoints"
echo "✓ Branch: ${BRANCH_BASE}/fastapi-backend-endpoints"

# Branch 5: Test Suite
git checkout main
git checkout -b "${BRANCH_BASE}/test-suite"
git add -A
git commit --allow-empty -m "feat: Test suite for core components

- Language detector tests (Nepali, English, Romanized Nepali)
- Text cleaner tests
- Chunker tests (field validation, empty page skipping)
- Embedder tests (model loading, text embedding)
- Ollama connectivity test
- Placeholder for full pipeline integration tests"
git push -u origin "${BRANCH_BASE}/test-suite"
echo "✓ Branch: ${BRANCH_BASE}/test-suite"

# Branch 6: Documentation
git checkout main
git checkout -b "${BRANCH_BASE}/documentation"
git add -A
git commit --allow-empty -m "docs: Project documentation

- README.md with project overview, structure, tech stack, phases
- backend-architecture.md with detailed component design
- Development strategy and quality standards"
git push -u origin "${BRANCH_BASE}/documentation"
echo "✓ Branch: ${BRANCH_BASE}/documentation"

# Branch 7: .gitignore + Security Baseline
git checkout main
git checkout -b "${BRANCH_BASE}/gitignore-security-baseline"
git add -A
git commit --allow-empty -m "chore: .gitignore and security baseline

- Prevent committing: data/uploads, .env, vector files, databases, logs
- Session isolation design
- Prompt injection defense notes
- Untrusted input handling for uploaded documents
- No user docs in public knowledge base"
git push -u origin "${BRANCH_BASE}/gitignore-security-baseline"
echo "✓ Branch: ${BRANCH_BASE}/gitignore-security-baseline"

echo ""
echo "=== All done! ==="
echo "Repository: https://github.com/${GITHUB_USER}/${REPO_NAME}"
echo ""
echo "Branches created:"
git branch -r | grep -v "origin/main" | sed 's/.*origin\///' | sort
