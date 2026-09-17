// API client for hamiGenZ backend
const BASE = "http://localhost:8000";

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
    const text = await res.text();
    throw new Error(`/explain failed (${res.status}): ${text}`);
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
    const text = await res.text();
    throw new Error(`/upload failed (${res.status}): ${text}`);
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

// Shared types for hamiGenZ backend API responses
// Kept in sync with backend Pydantic models
import type {
  ExplainResponse,
  UploadResponse,
  DocumentInfo,
  ViewerResponse,
  SearchResponse,
  ActionsResponse,
} from "./types";
