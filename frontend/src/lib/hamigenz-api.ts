// API client for hamiGenZ backend
// Resolve API base at build time via NEXT_PUBLIC_API_BASE_URL (staging/production)
// or fall back to localhost for development.
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

/**
 * Demo mode state.
 * When the backend is unreachable, these functions return clearly-labelled
 * static demo data instead of breaking the UX. Demo content is never
 * presented as live AI output.
 *
 * Default is on for the demo/preview branch so the panel renders without
 * a backend call; the toggle switches to Live mode.
 */
let demoMode = true;

export function setDemoModeState(enabled: boolean | ((prev: boolean) => boolean)) {
  demoMode = typeof enabled === "function" ? (enabled as (prev: boolean) => boolean)(demoMode) : enabled;
}

export function isDemo(): boolean {
  return demoMode;
}

export function getDemoMode(): boolean {
  return demoMode;
}

/** Check if the backend is reachable on build time (for static sites). */
function resolveApiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (configured && configured !== "http://127.0.0.1:8000" && configured !== "http://localhost:8000") {
    return configured;
  }
  return "http://127.0.0.1:8000";
}

export async function explainText(
  text: string,
  explanationLevel: "original" | "simple" | "very_simple",
  targetLanguage: string,
  question?: string,
  docId?: string
): Promise<ExplainResponse> {
  // Demo mode: return static sample explanation, never call the backend.
  if (isDemo()) {
    const demo = getDemoExplanations().find((d) => d.question.includes("passport"));
    return {
      explanation: {
        question: demo!.question,
        answer: demo!.answer,
        citations: demo!.citations,
        grounding: null,
        grounding_note: demo!.grounding_note || "Demo sample — not live AI output.",
        language: "english",
        explanation_level: "simple",
        evidence_pages: [1],
      },
      citations: demo!.citations,
      grounding: null,
      provenance: "document",
      language_used: "english",
      processing_time_ms: 0,
    };
  }
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

// ── Public API ─────────────────────────────────────────────────────────

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
  // Demo mode: return sample documents without calling the backend.
  if (isDemo()) {
    return [
      {
        doc_id: "demo-registration-form",
        filename: "registration_form_sample.pdf",
        upload_date: "2026-06-01T00:00:00Z",
        page_count: 1,
        language_hint: "english",
        status: "processed",
      },
    ];
  }
  const res = await fetch(`${BASE}/documents`);
  if (!res.ok) throw new Error(`/documents failed (${res.status})`);
  return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${BASE}/documents/${docId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`delete failed (${res.status})`);
}

export async function getDocumentViewer(docId: string): Promise<ViewerResponse> {
  // Demo mode: return sample document viewer data.
  if (isDemo() && docId === "demo-registration-form") {
    return {
      doc_id: docId,
      filename: "registration_form_sample.pdf",
      page_count: 1,
      pages: [
        {
          page_num: 1,
          text: "Registration form for the citizen: full name and contact details.",
          has_image: false,
          word_count: 10,
          },
          ],
          };
  }
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

export async function setFormFields(
  docId: string,
  values: FormFieldValue[]
): Promise<{ doc_id: string; count: number; saved: boolean }> {
  const res = await fetch(`${BASE}/documents/${docId}/form-fields`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ values }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`/form-fields failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export async function getFilledImage(
  docId: string,
  pageNum: number,
  values: FormFieldValue[]
): Promise<Blob> {
  const res = await fetch(
    `${BASE}/documents/${docId}/page/${pageNum}/fill-image`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values }),
    }
  );
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`/fill-image failed (${res.status}): ${detail}`);
  }
  return res.blob();
}

export async function submitFeedback(
  question: string,
  rating: number,
  docId?: string,
  comment?: string
): Promise<FeedbackResponse> {
  const res = await fetch(`${BASE}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, rating, doc_id: docId, comment }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`/feedback failed (${res.status}): ${detail}`);
  }
  return res.json();
}

// ── Demo mode data (clearly labelled as non-live) ────────────────────

const DEMO_EXPLANATIONS = [
  {
    question: "What documents are required for a Nepali passport application?",
    answer: "To apply for a Nepali passport, you need your old passport (if applicable), citizenship certificate, recent passport-size photographs, proof of address, and a completed application form. Minors require consent from parents or guardians. The exact list varies by applicant category.",
    citations: [
      { page: 1, excerpt: "Passport fees and required documents." },
      { page: 1, excerpt: "Minors require consent from parents or guardians." },
    ],
    language_used: "english",
    source: "dpa-official" as const,
    grounding_note: "Demo sample — not live AI output.",
  },
  {
    question: "How do I fill out a registration form?",
    answer: "To complete a citizen registration form, fill in your full name, father's name, date of birth, and county. Write clearly in ink, do not skip fields, and sign in the designated space. Attach required photographs and supporting documents as specified.",
    citations: [
      { page: 1, excerpt: "Registration form for the citizen: full name and contact details." },
    ],
    language_used: "english",
    source: "dpa-manual" as const,
    grounding_note: "Demo sample — not live AI output.",
  },
];

export function getDemoExplanations(): typeof DEMO_EXPLANATIONS {
  return DEMO_EXPLANATIONS;
}

/** Demo sample documents for the recruiter demo. */
export const DEMO_SAMPLE_DOCS = [
  {
    docId: "demo-registration-form",
    filename: "registration_form_sample.pdf",
    description: "Citizen registration form (sample)",
    descriptionLong: "A government registration form with fields for full name, father's name, date of birth, and county. Each field has a boxed answer area. This sample is used for form-field detection and reference-filled form preview.",
    pageCount: 1,
    previewImage: "",
    tags: ["registration", "form", "citizen"],
  },
];

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
  FeedbackResponse,
  FormFieldValue,
  FilledImageResponse,
} from "./types";
