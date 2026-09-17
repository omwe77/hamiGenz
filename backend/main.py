"""
hamigenz — FastAPI Backend
Main application entry point.
"""
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure the backend package is importable regardless of how the app is launched
# (uvicorn backend.main:app, python -m uvicorn, run.sh, IDE, etc.)
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Import local modules
from document_processor import DocumentProcessor, Chunker, MetadataStore
from vector_store import EmbeddingService, VectorStore, Pipeline
from llm_service import OllamaService, GroundingValidator, ExplanationEngine, LanguageDetector, VerificationLayer


# ─── Configuration ───────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
VECTORS_DIR = DATA_DIR / "vectors"
DB_PATH = DATA_DIR / "hamigenz.db"

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")


# ─── Lifespan ────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    print("[hamigenz] Starting up...")

    # Ensure directories
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    VECTORS_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize services
    app.state.embedder = EmbeddingService(model_name=EMBED_MODEL)
    app.state.vector_store = VectorStore(
        vectors_dir=str(VECTORS_DIR),
        dimension=app.state.embedder.dimension,
    )
    app.state.chunker = Chunker(chunk_size=500, overlap=50)
    app.state.metadata = MetadataStore(db_path=str(DB_PATH))
    app.state.ollama = OllamaService(base_url=OLLAMA_BASE, model=OLLAMA_MODEL)
    app.state.pipeline = Pipeline(
        embedding_service=app.state.embedder,
        vector_store=app.state.vector_store,
        chunker=app.state.chunker,
        metadata_store=app.state.metadata,
    )
    app.state.validator = GroundingValidator(app.state.ollama)
    app.state.verification = VerificationLayer(app.state.ollama, app.state.validator)
    app.state.explainer = ExplanationEngine(app.state.ollama)

    # Check Ollama connectivity
    try:
        models_resp = app.state.ollama._verify()
        print(f"[hamigenz] Ollama connected, model: {OLLAMA_MODEL}")
    except Exception as e:
        print(f"[hamigenz] Warning: Ollama may not be fully reachable: {e}")

    print(f"[hamigenz] Ready. Embedder: {EMBED_MODEL}, LLM: {OLLAMA_MODEL}")
    yield
    print("[hamigenz] Shutting down...")


# ─── App ─────────────────────────────────────────────────────────
app = FastAPI(
    title="hamigenz API",
    description="Nepal's AI Information & Document Understanding Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend — explicit origins only (wildcard + credentials is an
# invalid/unsafe combination and browsers reject it).
# Configure extra origins via CORS_EXTRA_ORIGINS (comma-separated).
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
CORS_ORIGINS = list({
    FRONTEND_ORIGIN,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    *[o.strip() for o in os.getenv("CORS_EXTRA_ORIGINS", "").split(",") if o.strip()],
})
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic Models ─────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str
    doc_id: Optional[str] = None
    language: str = "auto"  # auto, nepali, english, romanized_nepali


class AskResponse(BaseModel):
    question: str
    answer: str
    citations: list[dict]
    grounding_note: str
    evidence_pages: list[int]
    language_used: str
    processing_time_ms: Optional[int] = None


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    upload_date: str
    page_count: int
    language_hint: str
    status: str = "ready"


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    pages: int
    chunks: int
    language_hint: str
    message: str


class ExplainRequest(BaseModel):
    text: str
    doc_id: Optional[str] = None
    explanation_level: str = "simple"  # original, simple, very_simple
    target_language: str = "auto"  # auto, nepali, english, romanized_nepali
    question: Optional[str] = None  # optional context question


class ExplainResponse(BaseModel):
    explanation: dict
    citations: list[dict]
    grounding: dict | None
    provenance: str  # document, general_ai, mixed
    language_used: str
    processing_time_ms: Optional[int] = None


class ViewerPage(BaseModel):
    page_num: int
    text: str
    has_image: bool
    image_url: Optional[str] = None
    word_count: int


class SearchMatch(BaseModel):
    page: int
    text: str
    highlight_start: int
    highlight_end: int
    matched_term: str


class ViewerResponse(BaseModel):
    doc_id: str
    filename: str
    page_count: int
    pages: list[ViewerPage]


class SearchResponse(BaseModel):
    doc_id: str
    query: str
    matches: list[SearchMatch]


# ─── Endpoints ───────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "hamigenz",
        "version": "0.1.0",
        "ollama_model": OLLAMA_MODEL,
        "embedder": EMBED_MODEL,
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
):
    """
    Upload a document (PDF, PNG, JPG, TIFF) for analysis.
    The document is processed, chunked, embedded, and indexed.
    """
    # Read file
    file_bytes = await file.read()
    if len(file_bytes) < 100:
        raise HTTPException(400, "File too small")

    if len(file_bytes) > 50 * 1024 * 1024:  # 50 MB limit
        raise HTTPException(400, "File too large (max 50 MB)")

    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()

    if ext not in (".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"):
        raise HTTPException(400, f"Unsupported file type: {ext}. Use PDF or image (PNG/JPG/TIFF).")

    # Save file
    processor = DocumentProcessor(upload_dir=str(UPLOAD_DIR))
    filepath, doc_id = processor.save_upload(file_bytes, filename)

    # Process
    pipeline = app.state.pipeline
    result = pipeline.process_document(str(filepath), doc_id, filename)

    if result["status"] == "error":
        # Cleanup file on error
        Path(filepath).unlink(missing_ok=True)
        raise HTTPException(400, result.get("message", "Processing failed"))

    return UploadResponse(
        doc_id=doc_id,
        filename=filename,
        pages=result["pages"],
        chunks=result["chunks"],
        language_hint=result["language_hint"],
        message=f"Document processed successfully. {result['chunks']} chunks indexed.",
    )


@app.post("/ask", response_model=AskResponse)
async def ask_question(req: AskRequest):
    """
    Ask a question about a document or general Nepal information.

    If doc_id is provided, search within that document.
    Otherwise, search across all uploaded documents.
    """
    import time
    start = time.time()

    pipeline = app.state.pipeline
    validator = app.state.validator
    explainer = app.state.explainer
    detector = LanguageDetector()

    # Detect language
    detected_lang = detector.detect(req.question)
    if req.language == "auto":
        response_lang = detected_lang
    else:
        response_lang = req.language

    # Retrieve evidence
    evidence = pipeline.query(req.doc_id, req.question, top_k=5)

    if not evidence:
        return AskResponse(
            question=req.question,
            answer=(f"I could not find relevant information about \"{req.question}\" "
                    f"in the uploaded documents. Try uploading a relevant document or "
                    f"asking a different question."),
            citations=[],
            grounding_note="No evidence retrieved from documents.",
            evidence_pages=[],
            language_used=response_lang,
            processing_time_ms=int((time.time() - start) * 1000),
        )

    # Generate raw answer using LLM
    context = "\n\n".join(
        f"[Page {e['page_num']}] {e['text'][:500]}" for e in evidence[:5]
    )

    llm = app.state.ollama

    # Detect if question is about filling a form
    is_form_question = any(
        kw in req.question.lower()
        for kw in ["fill", "bhar", " भर", "bhanera", "कसरी", "kasari", "sentref",
                    "submit", "gauge", "gaune", "how to"]
    )

    if is_form_question and evidence:
        # Form-filling explanation mode
        form_prompt = f"""You are hamiGenZ, helping a user understand and fill out a form.

The user asked: {req.question}

Relevant document content:
{context}

INSTRUCTIONS:
1. Explain what each relevant field in the form means in simple language.
2. If asked to show how to fill the form, create a SAMPLE filled version.
3. The sample must include these warnings prominently:
   - "SAMPLE"
   - "FOR EXPLANATION ONLY"
   - "NOT FOR SUBMISSION"
4. Never make it look like a real official document. Make it clearly a teaching example.
5. If the user's language is Nepali, respond in Nepali. If English, respond in English.
6. Include page references where relevant.

Respond with the explanation / sample form.
"""
        raw_answer = llm.generate(form_prompt)
    else:
        # Normal document question
        doc_prompt = f"""You are hamiGenZ, a helpful assistant that explains documents in simple language
for ordinary people in Nepal.

The user asked: {req.question}

Relevant document content (with page numbers):
{context}

INSTRUCTIONS:
1. Answer the user's question based ONLY on the provided document content.
2. Use simple, clear language. Explain technical or legal terms.
3. If the question is in Nepali, answer in Nepali. If English, answer in English.
4. Include page references where relevant, like (Page 3).
5. If information is not in the document, say you could not find it there.
6. Do NOT invent facts. Do not guess fees, deadlines, or legal requirements.
7. Structure the answer helpfully: what it is, what it means, what to do.

Respond with the answer directly.
"""
        raw_answer = llm.generate(doc_prompt)

    # Validate grounding + run verification layer
    verification = app.state.verification.verify(req.question, raw_answer, evidence)
    grounding = verification["grounding_report"]

    # If contradictions found, attempt a corrected answer
    final_answer = raw_answer
    if verification.get("contradiction_found"):
        corrected = app.state.verification.re_prompt_on_contradiction(
            req.question, raw_answer, evidence, verification
        )
        if corrected:
            final_answer = corrected
            # Re-validate the corrected answer
            verification = app.state.verification.verify(req.question, final_answer, evidence)
            grounding = verification["grounding_report"]

    # Format final answer
    formatted = explainer.format_answer(
        question=req.question,
        raw_answer=final_answer,
        evidence_chunks=evidence,
        grounding_report=grounding,
        lang=response_lang,
    )

    elapsed = int((time.time() - start) * 1000)
    formatted["processing_time_ms"] = elapsed

    return AskResponse(**formatted)


# ─── /explain: direct text explanation with level control ──────────

@app.post("/explain", response_model=ExplainResponse)
async def explain_text(req: ExplainRequest):
    """
    Explain difficult text in simple language.
    Works with or without a document.
    explanation_level: "original" | "simple" | "very_simple"
    """
    import time
    start = time.time()

    detector = LanguageDetector()
    detected_lang = detector.detect(req.text)

    # Determine response language
    if req.target_language == "auto":
        response_lang = detected_lang
    else:
        response_lang = req.target_language

    # Determine provenance
    has_doc = bool(req.doc_id)
    provenance = "general_ai"
    if has_doc:
        provenance = "document"

    llm = app.state.ollama
    explainer = app.state.explainer

    # If doc_id provided, retrieve evidence from that document
    if has_doc:
        pipeline = app.state.pipeline
        evidence = pipeline.query(req.doc_id, req.text, top_k=5)

        if evidence:
            # Document-grounded explanation
            context = "\n\n".join(
                f"[Page {e['page_num']}] {e['text'][:500]}" for e in evidence[:5]
            )

            if req.question:
                full_question = f"{req.question} (Context: {req.text})"
            else:
                full_question = f"Explain this text in simple language: {req.text}"

            raw_answer = llm.generate(
                f"""You are hamiGenZ, helping a user understand difficult information.

The user wants to understand this text:
{req.text}

Relevant document content (with page numbers):
{context}

QUESTION: {full_question}

EXPLANATION LEVEL: {req.explanation_level}
LEVEL GUIDANCE:
{explainer._level_guidance(req.explanation_level)}

INSTRUCTIONS:
1. Explain the meaning of the text according to the EXPLANATION LEVEL above.
2. Preserve the original meaning exactly -- simplify the language, not the facts.
3. Explain any technical, legal, or official terms in plain language.
4. Include page references where relevant, like (Page 3).
5. If information is not in the document, say so.
6. Do NOT invent facts. Do not guess fees, deadlines, or legal requirements.
7. Structure the answer: what it is, what it means, what to do.

TARGET LANGUAGE: {response_lang}

Respond with the answer directly in {response_lang}."""
            )

            # Run verification layer on the explanation
            verification = app.state.verification.verify(full_question, raw_answer, evidence)
            grounding = verification["grounding_report"]

            # If contradictions found, attempt a corrected explanation
            final_answer = raw_answer
            if verification.get("contradiction_found"):
                corrected = app.state.verification.re_prompt_on_contradiction(
                    full_question, raw_answer, evidence, verification
                )
                if corrected:
                    final_answer = corrected
                    verification = app.state.verification.verify(full_question, final_answer, evidence)
                    grounding = verification["grounding_report"]

            formatted = explainer.format_answer(
                question=full_question,
                raw_answer=final_answer,
                evidence_chunks=evidence,
                grounding_report=grounding,
                lang=response_lang,
                explanation_level=req.explanation_level,
            )
            elapsed = int((time.time() - start) * 1000)
            formatted["processing_time_ms"] = elapsed
            return ExplainResponse(
                explanation=formatted,
                citations=formatted["citations"],
                grounding=grounding,
                provenance="document",
                language_used=response_lang,
                processing_time_ms=elapsed,
            )
        else:
            # Document not found or no evidence — fall through to general_ai
            pass

    # General AI explanation (no document, or document had no evidence)
    full_question = req.question or f"Explain this text in simple language: {req.text}"

    general_prompt = f"""You are hamiGenZ, explaining difficult information in simple, clear language for ordinary people in Nepal.

EXPLANATION LEVEL: {req.explanation_level}
(The level guidance tells you exactly how to handle this level)

The text to explain:
{req.text}

QUESTION: {full_question}

INSTRUCTIONS:
1. Explain the meaning in simple, clear language.
2. Preserve the original meaning exactly -- simplify the language, not the facts.
3. Explain any technical, legal, or official terms in plain language.
4. If the text is in Nepali, respond in Nepali. If English, respond in English.
5. Do NOT invent facts.
6. Structure the answer: what it is, what it means, what to do.

Respond with the answer directly.
"""
    raw_answer = llm.generate(general_prompt)

    # For general AI, no evidence -> no grounding
    formatted = explainer.format_answer(
        question=full_question,
        raw_answer=raw_answer,
        evidence_chunks=[],
        grounding_report=None,
        lang=response_lang,
        explanation_level=req.explanation_level,
    )
    elapsed = int((time.time() - start) * 1000)
    formatted["processing_time_ms"] = elapsed

    return ExplainResponse(
        explanation=formatted,
        citations=[],
        grounding=None,
        provenance="general_ai",
        language_used=response_lang,
        processing_time_ms=elapsed,
    )


# ─── /documents/{doc_id}/viewer: per-page extracted text ──────────

@app.get("/documents/{doc_id}/viewer", response_model=ViewerResponse)
async def get_document_viewer(doc_id: str):
    """
    Return per-page extracted text and metadata for a document viewer.
    """
    metadata = app.state.metadata
    doc = metadata.get_document(doc_id)
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found")

    processor = DocumentProcessor(upload_dir=str(UPLOAD_DIR))
    pages = processor.extract_text(doc["filepath"])

    viewer_pages = []
    for p in pages:
        has_image = bool(p.get("has_images", False))
        image_url = None
        if has_image and p.get("img_ref"):
            image_url = f"/documents/{doc_id}/page/{p['page_num']}/image"

        viewer_pages.append(ViewerPage(
            page_num=p["page_num"],
            text=p["text"],
            has_image=has_image,
            image_url=image_url,
            word_count=len(p["text"].split()),
        ))

    return ViewerResponse(
        doc_id=doc_id,
        filename=doc["filename"],
        page_count=len(viewer_pages),
        pages=viewer_pages,
    )


# ─── /documents/{doc_id}/page/{page_num}/image: page image ────────

@app.get("/documents/{doc_id}/page/{page_num}/image")
async def get_page_image(doc_id: str, page_num: int):
    """
    Return the rendered image for a specific page (for scanned/image pages).
    """
    metadata = app.state.metadata
    doc = metadata.get_document(doc_id)
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found")

    processor = DocumentProcessor(upload_dir=str(UPLOAD_DIR))
    img_bytes = processor.render_page_image(doc["filepath"], page_num)

    if not img_bytes:
        raise HTTPException(404, f"Page {page_num} image not available")

    from fastapi.responses import Response
    return Response(content=img_bytes, media_type="image/png")


# ─── /documents/{doc_id}/search-text: search extracted text ───────

@app.get("/documents/{doc_id}/search-text", response_model=SearchResponse)
async def search_document_text(doc_id: str, query: str = Query(..., min_length=1)):
    """
    Search extracted text across pages. Returns matches with page + context + highlight offsets.
    """
    metadata = app.state.metadata
    doc = metadata.get_document(doc_id)
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found")

    processor = DocumentProcessor(upload_dir=str(UPLOAD_DIR))
    pages = processor.extract_text(doc["filepath"])

    query_lower = query.lower()
    matches = []
    for p in pages:
        page_text = p["text"]
        page_lower = page_text.lower()
        idx = 0
        while True:
            idx = page_lower.find(query_lower, idx)
            if idx == -1:
                break
            # Context window: 200 chars before + match + 200 after
            start = max(0, idx - 200)
            end = min(len(page_text), idx + len(query) + 200)
            context = page_text[start:end]
            # highlight offsets relative to `context`
            h_start = idx - start
            h_end = h_start + len(query)

            matches.append(SearchMatch(
                page=p["page_num"],
                text=context,
                highlight_start=h_start,
                highlight_end=h_end,
                matched_term=query,
            ))
            idx += len(query)  # move past this match

    return SearchResponse(
        doc_id=doc_id,
        query=query,
        matches=matches,
    )


@app.get("/documents", response_model=list[DocumentInfo])
async def list_documents():
    """List all uploaded documents for the current session."""
    docs = app.state.metadata.list_documents()
    return [
        DocumentInfo(
            doc_id=d["doc_id"],
            filename=d["filename"],
            upload_date=d["upload_date"],
            page_count=d["page_count"],
            language_hint=d.get("language_hint", "unknown"),
        )
        for d in docs
    ]


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and all its vectors."""
    metadata = app.state.metadata
    vector_store = app.state.vector_store

    if not metadata.get_document(doc_id):
        raise HTTPException(404, f"Document {doc_id} not found")

    doc = metadata.get_document(doc_id)
    filepath = doc.get("filepath")

    # Remove from vector store
    vector_store.remove_document(doc_id)

    # Remove from metadata
    metadata.delete_document(doc_id)

    # Remove file
    if filepath and Path(filepath).exists():
        Path(filepath).unlink()

    return {"status": "deleted", "doc_id": doc_id}


@app.post("/ask-general")
async def ask_general_question(
    question: str = Query(..., description="Your question about Nepal"),
    language: str = Query("auto", description="Response language"),
):
    """
    Ask a general Nepal-specific question without uploading a document.
    Uses Ollama with Nepal-focused instructions.
    """
    import time
    start = time.time()

    detector = LanguageDetector()
    detected_lang = detector.detect(question)
    response_lang = language if language != "auto" else detected_lang

    llm = app.state.ollama

    # Nepal-focused general question prompt
    general_prompt = f"""You are hamiGenZ, Nepal's AI information assistant.

The user asked: {question}

INSTRUCTIONS:
1. Answer based on your knowledge of Nepal, its government, laws, procedures, and services.
2. If the question is about current fees, deadlines, procedures, eligibility, or official requirements,
   be careful. State that information should be verified with official sources.
3. Always mention the type of official source the user should check.
4. Use simple, clear language in {response_lang}.
5. If the question is in Romanized Nepali, understand it naturally.
6. If you are not sure about something, say so rather than guessing confidently.
7. For government procedures, outline the general steps but advise confirming current details
   with the relevant department.

Response in {response_lang}:
"""
    answer = llm.generate(general_prompt)

    elapsed = int((time.time() - start) * 1000)

    return {
        "question": question,
        "answer": answer,
        "citations": [],
        "grounding_note": "This is a general answer based on AI knowledge. Verify important details with official sources.",
        "evidence_pages": [],
        "language_used": response_lang,
        "processing_time_ms": elapsed,
    }


@app.get("/")
async def root():
    return {
        "name": "hamigenz",
        "tagline": "Don't understand it? Ask hamiGenZ.",
        "version": "0.1.0",
        "endpoints": {
            "upload": "POST /upload",
            "ask": "POST /ask",
            "ask_general": "GET /ask-general",
            "list_documents": "GET /documents",
            "delete_document": "DELETE /documents/{doc_id}",
            "health": "GET /health",
        },
        "docs": "/docs",
    }


# ─── /endpoints — plain HTML index of all registered routes ─────

@app.get("/endpoints")
async def endpoints_index(request: Request):
    """Returns a plain HTML page listing all registered routes.

    Generated live from app.routes — never hardcoded.
    Groups routes by tag if available, else lists them.
    Excludes the root '/' endpoint (listed separately on /).
    """
    routes: list[dict] = []
    for route in app.routes:
        # Skip the root endpoint itself
        if hasattr(route, "path") and route.path == "/":
            continue
        # Only include routes that have a path
        if not hasattr(route, "path") or not route.path:
            continue
        methods = getattr(route, "methods", None)
        if not methods:
            continue
        method = next(iter(methods), "GET") if methods else "GET"
        if method == "HEAD":
            continue  # skip HEAD, implicitly registered with GET routes
        tags = getattr(route, "tags", None) or []
        # Prefer the endpoint's own docstring first line, then its summary
        endpoint = getattr(route, "endpoint", None)
        doc = (endpoint.__doc__ or "").strip().splitlines()[0] if endpoint and endpoint.__doc__ else ""
        description = doc or getattr(route, "summary", None) or "No description available"
        routes.append({
            "method": method,
            "path": route.path,
            "description": description,
            "tags": tags,
        })

    # Sort: by tag group first, then by path
    def sort_key(r):
        tag = r["tags"][0] if r["tags"] else "___uncategorized"
        return (tag, r["path"])

    routes.sort(key=sort_key)

    # Group by tag
    groups: dict[str, list[dict]] = {}
    for r in routes:
        tag = r["tags"][0] if r["tags"] else "Other"
        groups.setdefault(tag, []).append(r)

    ordered_groups = sorted(groups.keys())

    # Render HTML
    html = _render_endpoints_html(groups, ordered_groups)
    return html


def _render_endpoints_html(groups: dict[str, list[dict]], ordered_groups: list[str]) -> HTMLResponse:
    """Build plain HTML response for the endpoints index page."""
    html_parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="UTF-8" />',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0" />',
        "<title>hamiGenZ — Backend Endpoints</title>",
        "<style>",
        "  * { box-sizing: border-box; margin: 0; padding: 0; }",
        "  body {",
        "    background: #0d0d0d;",
        "    color: #e0e0e0;",
        "    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;",
        "    font-size: 14px;",
        "    line-height: 1.6;",
        "    padding: 24px;",
        "    min-height: 100vh;",
        "  }",
        "  .header {",
        "    margin-bottom: 28px;",
        '    border-bottom: 2px solid #c8520b;',
        "    padding-bottom: 16px;",
        "  }",
        "  .header h1 {",
        "    color: #c8520b;",
        "    font-size: 22px;",
        "    font-weight: 700;",
        "    letter-spacing: -0.3px;",
        "  }",
        "  .header p {",
        "    color: #888;",
        "    font-size: 13px;",
        "    margin-top: 4px;",
        "  }",
        "  .footer {",
        "    margin-top: 40px;",
        '    border-top: 1px solid #333;',
        "    padding-top: 12px;",
        "    color: #666;",
        "    font-size: 11px;",
        "  }",
        "  .group {",
        "    margin-bottom: 24px;",
        "  }",
        "  .group-name {",
        "    color: #aaa;",
        "    font-size: 11px;",
        "    text-transform: uppercase;",
        "    letter-spacing: 1.5px;",
        "    margin-bottom: 8px;",
        "    padding-left: 8px;",
        "  }",
        "  table {",
        "    width: 100%;",
        "    border-collapse: collapse;",
        "    background: #1a1a1a;",
        "    border-radius: 6px;",
        "    overflow: hidden;",
        "  }",
        "  th {",
        "    text-align: left;",
        "    color: #777;",
        "    font-size: 11px;",
        "    text-transform: uppercase;",
        "    letter-spacing: 1px;",
        "    padding: 8px 12px;",
        "    border-bottom: 1px solid #333;",
        "    background: #111;",
        "  }",
        "  td {",
        "    padding: 8px 12px;",
        "    border-bottom: 1px solid #222;",
        "    vertical-align: top;",
        "  }",
        "  tr:last-child td { border-bottom: none; }",
        "  .method {",
        "    display: inline-block;",
        "    padding: 2px 8px;",
        "    border-radius: 3px;",
        "    font-size: 11px;",
        "    font-weight: 600;",
        "    letter-spacing: 0.5px;",
        "    text-transform: uppercase;",
        "  }",
        "  .method-GET { background: #1e3a5f; color: #7dd3fc; }",
        "  .method-POST { background: #166534; color: #86efac; }",
        "  .method-PUT { background: #92400e; color: #fde68a; }",
        "  .method-DELETE { background: #991b1b; color: #fca5a5; }",
        "  .method-PATCH { background: #4c1d95; color: #c4b5fd; }",
        "  .path {",
        "    color: #e0e0e0;",
        "    font-family: 'Fira Code', 'JetBrains Mono', monospace;",
        "    font-size: 13px;",
        "  }",
        "  .desc {",
        "    color: #999;",
        "    font-size: 12px;",
        "    max-width: 500px;",
        "  }",
        "  .empty {",
        "    color: #555;",
        "    font-style: italic;",
        "    padding: 8px 12px;",
        "    font-size: 12px;",
        "  }",
        "</style>",
        "</head>",
        "<body>",
        '<div class="header">',
        "  <h1>hamiGenZ — Backend Endpoints</h1>",
        "  <p>Live API reference — auto-generated from the running server's registered routes. Updates automatically when endpoints change.</p>",
        "</div>",
    ]

    for tag in ordered_groups:
        items = groups[tag]
        html_parts.append(f'<div class="group">')
        html_parts.append(f'  <div class="group-name">{tag}</div>')
        html_parts.append("  <table>")
        html_parts.append("    <tr><th>Method</th><th>Path</th><th>Description</th></tr>")
        for r in items:
            method = r["method"]
            path = r["path"]
            desc = r["description"]
            html_parts.append(
                f'    <tr>'
                f'      <td><span class="method method-{method}">{method}</span></td>'
                f'      <td class="path">{path}</td>'
                f'      <td class="desc">{desc}</td>'
                f'    </tr>'
            )
        html_parts.append("  </table>")
        html_parts.append("</div>")

    html_parts.append('<div class="footer">')
    html_parts.append("  <strong>hamiGenZ</strong> — Don't understand it? Ask hamiGenZ.")
    html_parts.append("</div>")
    html_parts.append("</body>")
    html_parts.append("</html>")

    return HTMLResponse(content="".join(html_parts), media_type="text/html")


# ─── Run ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
