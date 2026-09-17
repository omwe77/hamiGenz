// Shared types for hamiGenZ backend API responses
// Kept in sync with backend Pydantic models

export interface AskResponse {
  question: string;
  answer: string;
  citations: Citation[];
  grounding_note: string;
  evidence_pages: number[];
  language_used: string;
  processing_time_ms?: number;
}

export interface ExplainResponse {
  explanation: ExplanationData;
  citations: Citation[];
  grounding: GroundingReport | null;
  provenance: "document" | "general_ai" | "mixed";
  language_used: string;
  processing_time_ms?: number;
}

export interface ExplanationData {
  question: string;
  answer: string;
  citations: Citation[];
  grounding: GroundingReport | null;
  grounding_note: string;
  language: string;
  explanation_level: string;
  evidence_pages: number[];
  processing_time_ms?: number;
}

export interface Citation {
  page: number;
  excerpt: string;
  chunk_id?: string;
  start_offset?: number;
  end_offset?: number;
  source_type?: string;
}

export interface GroundingReport {
  claims?: Claim[];
  overall_confidence?: "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";
  missing_evidence?: string[];
  warning?: string;
  // STEP 3 verification layer fields
  contradiction_found?: boolean;
  contradiction_claims?: string[];
  confidence_score?: number;
  confidence_band?: "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";
  unsupported_facts?: string[];
  recommendation?: string;
}

export interface Claim {
  claim: string;
  classification: "SUPPORTED" | "PARTIALLY_SUPPORTED" | "CONTRADICTED" | "INSUFFICIENT_EVIDENCE";
  evidence: string;
  page_refs?: number[];
}

export interface UploadResponse {
  doc_id: string;
  filename: string;
  pages: number;
  chunks: number;
  language_hint: string;
  message: string;
}

export interface DocumentInfo {
  doc_id: string;
  filename: string;
  upload_date: string;
  page_count: number;
  language_hint: string;
  status: string;
}

export interface ViewerPage {
  page_num: number;
  text: string;
  has_image: boolean;
  image_url?: string;
  word_count: number;
}

export interface ViewerResponse {
  doc_id: string;
  filename: string;
  page_count: number;
  pages: ViewerPage[];
}

export interface SearchMatch {
  page: number;
  text: string;
  highlight_start: number;
  highlight_end: number;
  matched_term: string;
}

export interface SearchResponse {
  doc_id: string;
  query: string;
  matches: SearchMatch[];
}
