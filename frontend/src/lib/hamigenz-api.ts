// API client for hamiGenZ backend
// On public deployments (Vercel) without NEXT_PUBLIC_API_BASE_URL,
// the client operates safely in offline Demo Mode with curated civic document samples.
// Never calls 127.0.0.1 or localhost when deployed.

import type {
  ExplainResponse,
  UploadResponse,
  DocumentInfo,
  ViewerResponse,
  SearchResponse,
  SearchMatch,
  ActionsResponse,
  FormDetectResponse,
  FieldExplanation,
  AskGeneralResponse,
  FeedbackResponse,
  FormFieldValue,
} from "./types";

/**
 * Detect whether a live external backend is reachable.
 * In a public demo deployment (e.g. Vercel) without a dedicated external NEXT_PUBLIC_API_BASE_URL,
 * or where the configured URL points to localhost on a remote host, live mode is unavailable.
 */
export function hasLiveBackend(): boolean {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!configured) {
    if (typeof window !== "undefined") {
      const host = window.location.hostname;
      return host === "localhost" || host === "127.0.0.1";
    }
    return process.env.NODE_ENV !== "production";
  }
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host !== "localhost" && host !== "127.0.0.1") {
      if (configured.includes("localhost") || configured.includes("127.0.0.1")) {
        return false;
      }
    }
  }
  return true;
}

function getBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (configured) {
    if (typeof window !== "undefined") {
      const host = window.location.hostname;
      if (host !== "localhost" && host !== "127.0.0.1" && (configured.includes("localhost") || configured.includes("127.0.0.1"))) {
        return "";
      }
    }
    return configured.replace(/\/$/, "");
  }
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://127.0.0.1:8000";
    }
  }
  return "";
}

// ── Session & Credential Transport ────────────────────────────────────

let activeSessionToken: string | null = null;

export function getSessionToken(): string | null {
  if (activeSessionToken) return activeSessionToken;
  if (typeof window !== "undefined") {
    try {
      activeSessionToken = sessionStorage.getItem("hamigenz_session_token");
    } catch {
      // sessionStorage unavailable
    }
  }
  return activeSessionToken;
}

export function setSessionToken(token: string | null): void {
  activeSessionToken = token;
  if (typeof window !== "undefined" && token) {
    try {
      sessionStorage.setItem("hamigenz_session_token", token);
    } catch {
      // sessionStorage unavailable
    }
  }
}

/**
 * Standardized API fetch wrapper ensuring:
 * 1. credentials: "include" for HttpOnly cookies.
 * 2. X-Session-Token header sent for partitioned/cross-site browser scenarios.
 * 3. X-Requested-With: XMLHttpRequest sent for CSRF defense-in-depth.
 * 4. Automatic capture of new/refreshed X-Session-Token from response headers.
 */
export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  const token = getSessionToken();
  if (token) {
    headers.set("X-Session-Token", token);
  }
  headers.set("X-Requested-With", "XMLHttpRequest");

  const response = await fetch(input, {
    ...init,
    headers,
    credentials: "include",
  });

  const returnedToken = response.headers.get("X-Session-Token");
  if (returnedToken) {
    setSessionToken(returnedToken);
  }

  return response;
}

/**
 * Demo mode state.
 * When the backend is unreachable or not configured, these functions return clearly-labelled
 * static demo data instead of breaking the UX. Demo content is never presented as live AI output.
 */
let demoMode = true;

export function setDemoModeState(enabled: boolean | ((prev: boolean) => boolean)): boolean {
  if (!hasLiveBackend()) {
    demoMode = true;
    return false;
  }
  demoMode = typeof enabled === "function" ? (enabled as (prev: boolean) => boolean)(demoMode) : enabled;
  return demoMode;
}

export function isDemo(): boolean {
  if (!hasLiveBackend()) {
    return true;
  }
  return demoMode;
}

export function getDemoMode(): boolean {
  return isDemo();
}

// ── Public sample documents (demo purposes only) ─────────────────────

export const DEMO_SAMPLE_DOCS = [
  {
    docId: "demo-registration-form",
    filename: "registration_form_sample.pdf",
    description: "Citizen registration form (sample)",
    descriptionLong: "A government registration form with fields for full name, father's name, date of birth, district, and contact number. Each field has a boxed answer area. Used for form-field detection and reference-filled form preview.",
    pageCount: 1,
    previewImage: "/registration_form_sample.png",
    tags: ["registration", "form", "citizen", "sample"],
  },
];

const DEMO_VIEWER_TEXT = `नेपाल सरकार — नागरिक दर्ता तथा राहदानी सूचना प्रारूप (नमूना कागजात)
Government of Nepal — Citizen Registration & Civic Document Notice (Sample Document)

1. General Registration Instructions:
Registration form for the citizen: full name and contact details. Please enter your full name, father's name, date of birth, district, and contact telephone clearly in block letters. Ensure all details match your official citizenship certificate or birth record.

2. Passport Application & Renewal Requirements (Reference Excerpt):
Passport fees and required documents: Applicants must submit their original citizenship certificate, previous passport (if renewal), two recent passport-size photographs with white background, and proof of residence.
Minors require consent from parents or guardians along with certified copy of birth registration.

3. Submission & Fees:
Standard processing fee is NPR 5,000 for regular issuance through District Administration Offices. Fast-track emergency issuance at the Central Department of Passports requires NPR 12,000. All applicants must confirm biometric scheduling prior to visiting the office.`;

const DEMO_PASSPORT_EXPLANATION: ExplainResponse = {
  explanation: {
    question: "What documents are required for a Nepali passport application?",
    answer: "To apply for or renew a Nepali passport, you need your citizenship certificate (नागरिकता प्रमाणपत्र), previous passport (if renewal), two recent passport-size photographs with a white background, proof of permanent residence, and the completed application form. Minors require parental/guardian consent and a birth certificate.",
    citations: [
      { page: 1, excerpt: "Passport fees and required documents." },
      { page: 1, excerpt: "Minors require consent from parents or guardians." },
    ],
    grounding: {
      overall_confidence: "HIGH",
      confidence_band: "HIGH",
      confidence_score: 0.94,
      claims: [
        {
          claim: "Applicants must provide citizenship certificate and photographs",
          classification: "SUPPORTED",
          evidence: "Passport fees and required documents: Applicants must submit their original citizenship certificate...",
          page_refs: [1],
        },
        {
          claim: "Minors require parental or guardian consent",
          classification: "SUPPORTED",
          evidence: "Minors require consent from parents or guardians along with certified copy of birth registration.",
          page_refs: [1],
        },
      ],
      unsupported_facts: [],
      contradiction_found: false,
      recommendation: "Evidence strongly verified against sample document notice.",
    },
    grounding_note: "Demo sample — illustrative civic document breakdown (not live AI output).",
    language: "english",
    explanation_level: "simple",
    evidence_pages: [1],
    processing_time_ms: 0,
  },
  citations: [
    { page: 1, excerpt: "Passport fees and required documents." },
    { page: 1, excerpt: "Minors require consent from parents or guardians." },
  ],
  grounding: {
    overall_confidence: "HIGH",
    confidence_band: "HIGH",
    confidence_score: 0.94,
    claims: [
      {
        claim: "Applicants must provide citizenship certificate and photographs",
        classification: "SUPPORTED",
        evidence: "Passport fees and required documents: Applicants must submit their original citizenship certificate...",
        page_refs: [1],
      },
      {
        claim: "Minors require parental or guardian consent",
        classification: "SUPPORTED",
        evidence: "Minors require consent from parents or guardians along with certified copy of birth registration.",
        page_refs: [1],
      },
    ],
    unsupported_facts: [],
    contradiction_found: false,
    recommendation: "Evidence strongly verified against sample document notice.",
  },
  provenance: "document",
  language_used: "english",
  processing_time_ms: 0,
};

const DEMO_REGISTRATION_EXPLANATION: ExplainResponse = {
  explanation: {
    question: "How do I fill out a registration form?",
    answer: "To complete the citizen registration form, write your full legal name, father's name, date of birth, permanent district, and phone number in the boxed answer sections. Always match the spelling with your Nepali citizenship certificate. Do not leave required identity boxes blank, and sign in the designated citizen signature box.",
    citations: [
      { page: 1, excerpt: "Registration form for the citizen: full name and contact details." },
    ],
    grounding: {
      overall_confidence: "HIGH",
      confidence_band: "HIGH",
      confidence_score: 0.96,
      claims: [
        {
          claim: "Citizen registration requires full name and contact details matching official records",
          classification: "SUPPORTED",
          evidence: "Registration form for the citizen: full name and contact details. Please enter your full name...",
          page_refs: [1],
        },
      ],
      unsupported_facts: [],
      contradiction_found: false,
      recommendation: "Evidence verified against citizen registration instructions.",
    },
    grounding_note: "Demo sample — illustrative civic document breakdown (not live AI output).",
    language: "english",
    explanation_level: "simple",
    evidence_pages: [1],
    processing_time_ms: 0,
  },
  citations: [
    { page: 1, excerpt: "Registration form for the citizen: full name and contact details." },
  ],
  grounding: {
    overall_confidence: "HIGH",
    confidence_band: "HIGH",
    confidence_score: 0.96,
    claims: [
      {
        claim: "Citizen registration requires full name and contact details matching official records",
        classification: "SUPPORTED",
        evidence: "Registration form for the citizen: full name and contact details. Please enter your full name...",
        page_refs: [1],
      },
    ],
    unsupported_facts: [],
    contradiction_found: false,
    recommendation: "Evidence verified against citizen registration instructions.",
  },
  provenance: "document",
  language_used: "english",
  processing_time_ms: 0,
};

const DEMO_EXPLANATIONS = [
  {
    question: DEMO_PASSPORT_EXPLANATION.explanation.question,
    answer: DEMO_PASSPORT_EXPLANATION.explanation.answer,
    citations: DEMO_PASSPORT_EXPLANATION.citations,
    language_used: "english",
    source: "dpa-official" as const,
    grounding_note: DEMO_PASSPORT_EXPLANATION.explanation.grounding_note,
  },
  {
    question: DEMO_REGISTRATION_EXPLANATION.explanation.question,
    answer: DEMO_REGISTRATION_EXPLANATION.explanation.answer,
    citations: DEMO_REGISTRATION_EXPLANATION.citations,
    language_used: "english",
    source: "dpa-manual" as const,
    grounding_note: DEMO_REGISTRATION_EXPLANATION.explanation.grounding_note,
  },
];

export function getDemoExplanations(): typeof DEMO_EXPLANATIONS {
  return DEMO_EXPLANATIONS;
}

const DEMO_ACTIONS_RESPONSE: ActionsResponse = {
  requirements: [
    "Original citizenship certificate and 1 clear photocopy (नागरिकता प्रमाणपत्र)",
    "Two passport-sized photographs (white background, borderless)",
    "Proof of permanent address (वडा सिफारिस / utility bill)",
    "Completed citizen registration application form (sample form)",
  ],
  deadlines: [
    { date: "Within 35 days", description: "Submission window following local ward recommendation" },
    { date: "Standard 15 days", description: "Standard turnaround for non-urgent processing" },
  ],
  fees: [
    { amount: "NPR 5,000", description: "Standard passport processing fee (regular service)" },
    { amount: "NPR 12,000", description: "Urgent same-day dispatch fee at Central Department of Passports" },
  ],
  eligibility: [
    "Nepali citizen holding valid citizenship card or minor identification certificate",
    "Consent letter from parent/guardian for applicants under 18 years of age",
  ],
  next_steps: [
    "Verify details on your filled registration sample form",
    "Gather supporting identity documents and photographs",
    "Book an appointment slot at your local District Administration Office (DAO) or online portal",
    "Visit the designated counter for biometric verification and fee deposit",
  ],
  official_links: [
    {
      url: "https://nepal.gov.np",
      description: "Nepal Government National Portal (Verified Official)",
      classification: "verified_official",
      source_id: "gov-nepal",
      source_name: "Government of Nepal National Portal",
    },
    {
      url: "https://nepalpassport.gov.np",
      description: "Department of Passports Official Portal (Verified Official)",
      classification: "verified_official",
      source_id: "dop-nepal",
      source_name: "Department of Passports, Nepal",
    },
  ],
  meta: {
    status: "hints_only",
    note: "Demo sample — illustrative civic actions for recruiter exploration (not live AI output).",
  },
};

const DEMO_FORM_DETECTION: FormDetectResponse = {
  detection: {
    is_form: true,
    confidence: 0.95,
    field_count: 5,
    matched_keywords: ["नाम (Full Name)", "बाबुको नाम (Father's Name)", "जन्म मिति (Date of Birth)", "जिल्ला (District)", "सम्पर्क नम्बर (Phone Number)"],
  },
  fields: [
    { label: "Full Name (पूरा नाम)", page: 1, evidence: "Applicant full legal name matching citizenship certificate" },
    { label: "Father's Name (बाबुको नाम)", page: 1, evidence: "Father's name as stated in official records" },
    { label: "Date of Birth (जन्म मिति)", page: 1, evidence: "Date of birth in Bikram Sambat (BS) or AD format" },
    { label: "District (जिल्ला)", page: 1, evidence: "Permanent residential district" },
    { label: "Phone Number (सम्पर्क नम्बर)", page: 1, evidence: "10-digit mobile number for notification" },
  ],
};

function getDemoFieldExplanation(label: string): FieldExplanation {
  const norm = label.toLowerCase();
  if (norm.includes("father") || norm.includes("बाबु")) {
    return {
      meaning: "The legal full name of your father as registered in government documents.",
      belongs: "Enter exactly what appears under 'बाबुको नाम' on your Nepali citizenship certificate.",
      do_not_enter: "Do not enter grandfather's name, caste title alone, or informal nicknames.",
      example: "हरि प्रसाद श्रेष्ठ / Hari Prasad Shrestha",
      sample_format: "Nepali Devanagari or Latin letters as requested by the form",
      source_quote: "Registration form for the citizen: father's name as stated in official records.",
      page: 1,
      sample_markers: ["Illustrative sample", "Form helper"],
      meta: { status: "hints_only", note: "Demo sample guidance — not live legal advice." },
    };
  }
  if (norm.includes("birth") || norm.includes("जन्म")) {
    return {
      meaning: "Your official date of birth in Bikram Sambat (BS) or Christian Era (AD).",
      belongs: "Enter the year, month, and day matching your birth certificate or citizenship card.",
      do_not_enter: "Do not approximate or enter an unverified horoscope (चिना) date if it differs from official ID.",
      example: "२०५५/०३/१५ BS (1998-06-29 AD)",
      sample_format: "YYYY/MM/DD",
      source_quote: "Date of birth in Bikram Sambat (BS) or AD format.",
      page: 1,
      sample_markers: ["Illustrative sample", "Form helper"],
      meta: { status: "hints_only", note: "Demo sample guidance — not live legal advice." },
    };
  }
  if (norm.includes("district") || norm.includes("जिल्ला")) {
    return {
      meaning: "Your permanent administrative district in Nepal.",
      belongs: "Your permanent address district as listed in your citizenship certificate.",
      do_not_enter: "Do not write your temporary hostel or rental city unless asked for temporary address.",
      example: "कास्की / Kaski (or काठमाडौं / Kathmandu)",
      sample_format: "District name (Devanagari or English)",
      source_quote: "Permanent residential district.",
      page: 1,
      sample_markers: ["Illustrative sample", "Form helper"],
      meta: { status: "hints_only", note: "Demo sample guidance — not live legal advice." },
    };
  }
  if (norm.includes("phone") || norm.includes("सम्पर्क")) {
    return {
      meaning: "An active mobile phone number for SMS tracking and dispatch notifications.",
      belongs: "Your own primary 10-digit mobile number.",
      do_not_enter: "Do not enter a landline or overseas number without country code.",
      example: "9841000000",
      sample_format: "10-digit mobile number starting with 98 or 97",
      source_quote: "10-digit mobile number for notification.",
      page: 1,
      sample_markers: ["Illustrative sample", "Form helper"],
      meta: { status: "hints_only", note: "Demo sample guidance — not live legal advice." },
    };
  }
  return {
    meaning: `Official entry field for "${label}" on civic application forms.`,
    belongs: "Enter the details exactly matching your official citizenship certificate or government-issued ID.",
    do_not_enter: "Do not enter unofficial nicknames or shortened forms.",
    example: "राम बहादुर श्रेष्ठ / Ram Bahadur Shrestha",
    sample_format: "Standard Devanagari or Latin text",
    source_quote: "Applicant full legal name matching citizenship certificate.",
    page: 1,
    sample_markers: ["Illustrative sample", "Form helper"],
    meta: { status: "hints_only", note: "Demo sample guidance — not live legal advice." },
  };
}

const DEMO_ASK_GENERAL: AskGeneralResponse = {
  question: "What documents are required for a Nepali passport?",
  answer: "To apply for or renew a Nepali passport, standard requirements include your original citizenship certificate, previous passport (if renewal), passport-size photos with white background, and address verification. Appointments must be pre-booked at the Department of Passports or local DAO.",
  provenance: "official_source",
  citations: [
    { page: 1, excerpt: "Passport fees and required documents." },
  ],
  evidence_pages: [1],
  language_used: "english",
  official_sources: [
    {
      source_id: "gov-nepal",
      organization: "Government of Nepal",
      title: "Nepal Government National Portal",
      url: "https://nepal.gov.np",
      source_type: "portal",
      authority_level: "national",
      verified: true,
      status: "active",
      verified_date: "2026-06-01",
      fetched_date: "2026-06-01",
      excerpt: "Official guidelines for passport issuance and citizenship services.",
    },
    {
      source_id: "dop-nepal",
      organization: "Department of Passports",
      title: "Department of Passports Official Portal",
      url: "https://nepalpassport.gov.np",
      source_type: "department",
      authority_level: "departmental",
      verified: true,
      status: "active",
      verified_date: "2026-06-01",
      fetched_date: "2026-06-01",
      excerpt: "Online e-Passport application procedures and biometric scheduling.",
    },
  ],
  freshness: {
    verdict: "current",
    stale_sources: [],
    notes: "Verified against curated official sources registry (Demo sample).",
  },
  grounding_note: "Demo sample — illustrative answer from curated sources (not live AI output).",
  verification: {
    confidence_band: "HIGH",
    confidence_score: 0.95,
    unsupported_facts: [],
    contradiction_found: false,
    recommendation: "Information cross-referenced with Department of Passports guidelines.",
  },
  processing_time_ms: 0,
};

// ── Public API Implementation ──────────────────────────────────────────

export async function explainText(
  text: string,
  explanationLevel: "original" | "simple" | "very_simple",
  targetLanguage: string,
  question?: string,
  docId?: string
): Promise<ExplainResponse> {
  if (isDemo()) {
    const combined = `${text} ${question || ""}`.toLowerCase();
    const isReg = combined.includes("form") || combined.includes("registration") || combined.includes("दर्ता") || combined.includes("फारम");
    const demo = isReg ? DEMO_REGISTRATION_EXPLANATION : DEMO_PASSPORT_EXPLANATION;
    return {
      ...demo,
      explanation: {
        ...demo.explanation,
        question: question || demo.explanation.question,
        explanation_level: explanationLevel,
      },
      language_used: targetLanguage === "auto" ? "english" : targetLanguage,
      processing_time_ms: 0,
    };
  }

  const base = getBaseUrl();
  if (!base) throw new Error("Live backend not configured");
  const body: Record<string, unknown> = {
    text,
    explanation_level: explanationLevel,
    target_language: targetLanguage,
  };
  if (question) body.question = question;
  if (docId) body.doc_id = docId;

  const res = await apiFetch(`${base}/explain`, {
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
  if (isDemo()) {
    return {
      doc_id: `demo-local-${Date.now()}`,
      filename: file.name,
      pages: 1,
      chunks: 1,
      language_hint: "auto",
      message: "Demo mode: Document received locally in browser memory only; not transmitted to any server.",
      upload_date: new Date().toISOString(),
      page_count: 1,
      status: "demo-local",
    };
  }

  const base = getBaseUrl();
  if (!base) throw new Error("Live backend not configured");
  const form = new FormData();
  form.append("file", file);
  const res = await apiFetch(`${base}/upload`, {
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
  if (isDemo()) {
    return DEMO_SAMPLE_DOCS.map((d) => ({
      doc_id: d.docId,
      filename: d.filename,
      upload_date: "2026-06-01T00:00:00Z",
      page_count: d.pageCount,
      language_hint: "english",
      status: "processed",
    }));
  }

  const base = getBaseUrl();
  if (!base) throw new Error("Live backend not configured");
  const res = await apiFetch(`${base}/documents`);
  if (!res.ok) throw new Error(`/documents failed (${res.status})`);
  return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  if (isDemo()) {
    return;
  }

  const base = getBaseUrl();
  if (!base) throw new Error("Live backend not configured");
  const res = await apiFetch(`${base}/documents/${docId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`delete failed (${res.status})`);
}

export async function getDocumentViewer(docId: string): Promise<ViewerResponse> {
  if (isDemo()) {
    if (docId === "demo-registration-form") {
      return {
        doc_id: docId,
        filename: "registration_form_sample.pdf",
        page_count: 1,
        pages: [
          {
            page_num: 1,
            text: DEMO_VIEWER_TEXT,
            has_image: true,
            image_url: "/registration_form_sample.png",
            word_count: 124,
          },
        ],
      };
    }
    if (docId.startsWith("demo-local-")) {
      return {
        doc_id: docId,
        filename: "uploaded_sample.txt",
        page_count: 1,
        pages: [
          {
            page_num: 1,
            text: "Demo Mode Note: Live OCR and vector indexing require the self-hosted backend. In this public portfolio demo, files are kept strictly in local memory and not processed on a remote server.",
            has_image: false,
            word_count: 32,
          },
        ],
      };
    }
    throw new Error(`Document ${docId} not found in demo mode`);
  }

  const base = getBaseUrl();
  if (!base) throw new Error("Live backend not configured");
  const res = await apiFetch(`${base}/documents/${docId}/viewer`);
  if (!res.ok) throw new Error(`viewer failed (${res.status})`);
  return res.json();
}

export async function searchDocumentText(
  docId: string,
  query: string
): Promise<SearchResponse> {
  if (isDemo()) {
    const q = query.trim().toLowerCase();
    const matches: SearchMatch[] = [];
    if (q) {
      const viewer = await getDocumentViewer(docId);
      for (const page of viewer.pages) {
        const text = page.text;
        const lowerText = text.toLowerCase();
        let idx = 0;
        while ((idx = lowerText.indexOf(q, idx)) !== -1) {
          const end = idx + q.length;
          const winStart = Math.max(0, idx - 25);
          const winEnd = Math.min(text.length, end + 25);
          matches.push({
            page: page.page_num,
            text: text.slice(winStart, winEnd),
            highlight_start: idx - winStart,
            highlight_end: end - winStart,
            matched_term: text.slice(idx, end),
          });
          idx = end;
        }
      }
    }
    return {
      doc_id: docId,
      query,
      matches,
    };
  }

  const base = getBaseUrl();
  if (!base) throw new Error("Live backend not configured");
  const res = await apiFetch(
    `${base}/documents/${docId}/search-text?query=${encodeURIComponent(query)}`
  );
  if (!res.ok) throw new Error(`search failed (${res.status})`);
  return res.json();
}

export async function extractActions(
  text?: string,
  docId?: string,
  question?: string
): Promise<ActionsResponse> {
  if (isDemo()) {
    return DEMO_ACTIONS_RESPONSE;
  }

  const base = getBaseUrl();
  if (!base) throw new Error("Live backend not configured");
  const body: Record<string, unknown> = {};
  if (text) body.text = text;
  if (docId) body.doc_id = docId;
  if (question) body.question = question;
  const res = await apiFetch(`${base}/actions`, {
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
  if (isDemo()) {
    return {
      ...DEMO_ASK_GENERAL,
      question,
      language_used: language === "auto" ? "english" : language,
    };
  }

  const base = getBaseUrl();
  if (!base) throw new Error("Live backend not configured");
  const res = await apiFetch(
    `${base}/ask-general?question=${encodeURIComponent(question)}&language=${encodeURIComponent(language)}`,
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
  if (isDemo()) {
    return DEMO_FORM_DETECTION;
  }

  const base = getBaseUrl();
  if (!base) throw new Error("Live backend not configured");
  const body: Record<string, unknown> = {};
  if (text) body.text = text;
  if (docId) body.doc_id = docId;
  const res = await apiFetch(`${base}/forms/detect`, {
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
  if (isDemo()) {
    return getDemoFieldExplanation(label);
  }

  const base = getBaseUrl();
  if (!base) throw new Error("Live backend not configured");
  const body: Record<string, unknown> = { label };
  if (opts.docId) body.doc_id = opts.docId;
  if (opts.context) body.context = opts.context;
  if (opts.page) body.page = opts.page;
  if (opts.language) body.language = opts.language;
  if (opts.question) body.question = opts.question;
  const res = await apiFetch(`${base}/forms/explain-field`, {
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
  if (isDemo()) {
    return { doc_id: docId, count: values.length, saved: true };
  }

  const base = getBaseUrl();
  if (!base) throw new Error("Live backend not configured");
  const res = await apiFetch(`${base}/documents/${docId}/form-fields`, {
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
  if (isDemo()) {
    return new Blob([], { type: "image/png" });
  }

  const base = getBaseUrl();
  if (!base) throw new Error("Live backend not configured");
  const res = await apiFetch(
    `${base}/documents/${docId}/page/${pageNum}/fill-image`,
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
  if (isDemo()) {
    return {
      status: "received",
      rating,
      feedback_id: 1,
      aggregate: {
        total: 42,
        up: rating > 0 ? 39 : 38,
        down: rating < 0 ? 4 : 3,
        up_rate: 0.93,
      },
    };
  }

  const base = getBaseUrl();
  if (!base) throw new Error("Live backend not configured");
  const res = await apiFetch(`${base}/feedback`, {
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
