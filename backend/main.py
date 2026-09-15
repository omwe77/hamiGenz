"""
hamigenz — FastAPI Backend
Main application entry point.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Import local modules
from document_processor import DocumentProcessor, Chunker, MetadataStore
from vector_store import EmbeddingService, VectorStore, Pipeline
from llm_service import OllamaService, GroundingValidator, ExplanationEngine, LanguageDetector


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

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


# ─── Helper: session isolation ───────────────────────────────────
def _get_session_id(request) -> str:
    """Extract or generate session ID from request header."""
    return request.headers.get("X-Session-ID", "default-session")


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

    # Validate grounding
    grounding = validator.validate(req.question, raw_answer, evidence)

    # Format final answer
    formatted = explainer.format_answer(
        question=req.question,
        raw_answer=raw_answer,
        evidence_chunks=evidence,
        grounding_report=grounding,
        lang=response_lang,
    )

    elapsed = int((time.time() - start) * 1000)
    formatted["processing_time_ms"] = elapsed

    return AskResponse(**formatted)


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


# ─── Run ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
