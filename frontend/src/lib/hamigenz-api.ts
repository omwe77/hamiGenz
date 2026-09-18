// API client for hamiGenZ backend
// Resolve API base at build time via NEXT_PUBLIC_API_BASE_URL (staging/production)
// or fall back to localhost for development.
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export async function explainText(
  text: string,
  explanationLevel: "original" | "simple" | "very_simple",
  targetLanguage: string,
  question?: string,
  docId?: string
): Promise<ExplainResponse> {
  const body: Record<string, unknown> = {
    text,
    explanation_level: explanationLevel,
    target_language: targetLanguage,
  };
  if (question) body.question = question;
  if (docId) body.doc_id = docId;

  const res = await fetch(`${BASE}/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`/explain failed (${res.status}): ${errText}`);
  }
  return res.json();
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`/upload failed (${res.status}): ${errText}`);
  }
  return res.json();
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${BASE}/documents`);
  if (!res.ok) throw new Error(`/documents failed (${res.status})`);
  return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${BASE}/documents/${docId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`delete failed (${res.status})`);
}

export async function getDocumentViewer(docId: string): Promise<ViewerResponse> {
  const res = await fetch(`${BASE}/documents/${docId}/viewer`);
  if (!res.ok) throw new Error(`viewer failed (${res.status})`);
  return res.json();
}

export async function searchDocumentText(
  docId: string,
  query: string
): Promise<SearchResponse> {
  const res = await fetch(
    `${BASE}/documents/${docId}/search-text?query=${encodeURIComponent(query)}`
  );
  if (!res.ok) throw new Error(`search failed (${res.status})`);
  return res.json();
}

export async function extractActions(
  text?: string,
  docId?: string,
  question?: string
): Promise<ActionsResponse> {
  const body: Record<string, unknown> = {};
  if (text) body.text = text;
  if (docId) body.doc_id = docId;
  if (question) body.question = question;
  const res = await fetch(`${BASE}/actions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`/actions failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export async function askGeneral(
  question: string,
  language: string = "auto"
): Promise<AskGeneralResponse> {
  const res = await fetch(
    `${BASE}/ask-general?question=${encodeURIComponent(question)}&language=${encodeURIComponent(language)}`,
    { method: "POST" }
  );
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`/ask-general failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export async function detectFormFields(
  text?: string,
  docId?: string
): Promise<FormDetectResponse> {
  const body: Record<string, unknown> = {};
  if (text) body.text = text;
  if (docId) body.doc_id = docId;
  const res = await fetch(`${BASE}/forms/detect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`/forms/detect failed (${res.status})`);
  return res.json();
}

export async function explainFormField(
  label: string,
  opts: { docId?: string; context?: string; page?: number; language?: string; question?: string }
): Promise<FieldExplanation> {
  const body: Record<string, unknown> = { label };
  if (opts.docId) body.doc_id = opts.docId;
  if (opts.context) body.context = opts.context;
  if (opts.page) body.page = opts.page;
  if (opts.language) body.language = opts.language;
  if (opts.question) body.question = opts.question;
  const res = await fetch(`${BASE}/forms/explain-field`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`/forms/explain-field failed (${res.status}): ${detail}`);
  }
  return res.json();
}

// Shared types for hamiGenZ backend API responses
// Kept in sync with backend Pydantic models
import type {
  ExplainResponse,
  UploadResponse,
  DocumentInfo,
  ViewerResponse,
  SearchResponse,
  ActionsResponse,
  FormDetectResponse,
  FieldExplanation,
  AskGeneralResponse,
} from "./types";
