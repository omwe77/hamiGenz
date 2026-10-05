"use client";

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import Link from "next/link";
import {
  explainText,
  uploadDocument,
  listDocuments,
  deleteDocument,
  getDocumentViewer,
  searchDocumentText,
  extractActions,
  submitFeedback,
} from "@/lib/hamigenz-api";
import type {
  ViewerPage,
  ExplainResponse,
  DocumentInfo,
  SearchMatch,
  Citation,
  ActionsResponse,
  FeedbackResponse,
} from "@/lib/types";
import ExplanationLevelSelect from "./ExplanationLevelSelect";
import ExplanationPanel from "./ExplanationPanel";
import DocumentViewer from "./DocumentViewer";
import ProvenanceBadge from "./ProvenanceBadge";
import ActionPanel from "./ActionPanel";
import FormPanel from "./FormPanel";

// ── Types ──────────────────────────────────────────────────────────────
type ExplainLevel = "original" | "simple" | "very_simple";
type TargetLang = "auto" | "nepali" | "english" | "romanized_nepali";

const EXAMPLE_PROMPTS = [
  { tag: "📜 Notice", text: "यो सूचनामा वास्तवमा के भन्न खोजिएको हो?" },
  { tag: "🔤 Romanized", text: "yo notice ko simple meaning ke ho?" },
  { tag: "🛂 Passport", text: "passport banauna k k chainxa?" },
  { tag: "📋 Checklist", text: "What do I need to submit?" },
];

export default function WorkspacePage() {
  // ── Explain state ───────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<"explain" | "document" | "split">("explain");
  const [isDragging, setIsDragging] = useState(false);
  const [explainLevel, setExplainLevel] = useState<ExplainLevel>("simple");
  const [targetLang, setTargetLang] = useState<TargetLang>("auto");
  const [inputText, setInputText] = useState("");
  const [question, setQuestion] = useState("");
  const [explanation, setExplanation] = useState<ExplainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Document state ──────────────────────────────────────────────────
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [viewerData, setViewerData] = useState<{ docId: string | null; pages: ViewerPage[] }>({
    docId: null,
    pages: [],
  });
  const viewerLoading = Boolean(activeDocId && viewerData.docId !== activeDocId);
  const viewerPages = viewerData.docId === activeDocId ? viewerData.pages : [];
  const [selectedText, setSelectedText] = useState("");

  // ── Search state ────────────────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchMatch[]>([]);
  const [activeSearchMatchIdx, setActiveSearchMatchIdx] = useState<number | null>(null);

  // ── Citation/highlight state (pure derived state from explanation) ───
  const [highlightPage, setHighlightPage] = useState<number | null>(null);

  const citationsByPage = useMemo(() => {
    const map = new Map<number, Citation[]>();
    if (explanation?.citations) {
      for (const c of explanation.citations) {
        const list = map.get(c.page) || [];
        list.push(c);
        map.set(c.page, list);
      }
    }
    return map;
  }, [explanation]);

  // ── Action layer state (PR-009) ─────────────────────────────────────
  const [actions, setActions] = useState<ActionsResponse | null>(null);
  const [actionsLoading, setActionsLoading] = useState(false);
  const [actionsError, setActionsError] = useState<string | null>(null);

  // ── Feedback state (thumbs up/down on explanations) ────────────────────
  const [feedback, setFeedback] = useState<{
    rating: number | null;
    confirmed: boolean;
    aggregate: FeedbackResponse["aggregate"] | null;
  }>({ rating: null, confirmed: false, aggregate: null });

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Load documents once ─────────────────────────────────────────────
  useEffect(() => {
    listDocuments().then(setDocuments).catch(() => {});
  }, []);

  // ── Active doc → load viewer ────────────────────────────────────────
  useEffect(() => {
    if (!activeDocId) {
      return;
    }
    let ignore = false;
    getDocumentViewer(activeDocId)
      .then((v) => {
        if (!ignore) setViewerData({ docId: activeDocId, pages: v.pages });
      })
      .catch(() => {
        if (!ignore) setViewerData({ docId: activeDocId, pages: [] });
      });
    return () => {
      ignore = true;
    };
  }, [activeDocId]);

  // ── Debounced search on active doc ──────────────────────────────────
  useEffect(() => {
    if (!activeDocId || !searchQuery.trim()) {
      return;
    }
    let ignore = false;
    const t = setTimeout(() => {
      searchDocumentText(activeDocId, searchQuery.trim())
        .then((r) => {
          if (!ignore) {
            setSearchResults(r.matches);
            setActiveSearchMatchIdx(null);
          }
        })
        .catch(() => {
          if (!ignore) setSearchResults([]);
        });
    }, 300);
    return () => {
      ignore = true;
      clearTimeout(t);
    };
  }, [activeDocId, searchQuery]);

  // ── Core explain runner ─────────────────────────────────────────────
  const runExplain = useCallback(
    async (
      text: string,
      level: ExplainLevel,
      lang: TargetLang,
      q: string | undefined,
      docId: string | undefined
    ) => {
      setLoading(true);
      setError(null);
      setExplanation(null);
      try {
        const res = await explainText(text, level, lang, q, docId);
        setExplanation(res);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const handleExplain = useCallback(() => {
    if (!inputText.trim() || loading) return;
    runExplain(
      inputText.trim(),
      explainLevel,
      targetLang,
      question.trim() || undefined,
      activeDocId || undefined
    );
  }, [inputText, loading, explainLevel, targetLang, question, activeDocId, runExplain]);

  // ── Explain the selected text directly (fresh values, no stale state) ──
  const explainFromSelection = useCallback(
    (text: string) => {
      if (!text.trim()) return;
      setActiveTab("explain");
      setInputText(text);
      runExplain(
        text,
        explainLevel,
        targetLang,
        question.trim() || undefined,
        activeDocId || undefined
      );
    },
    [explainLevel, targetLang, question, activeDocId, runExplain]
  );

  // ── Upload ──────────────────────────────────────────────────────────
  const handleFile = useCallback(async (file: File) => {
    try {
      const res = await uploadDocument(file);
      setDocuments((prev) => [
        ...prev,
        {
          doc_id: res.doc_id,
          filename: res.filename,
          upload_date: res.upload_date || new Date().toISOString(),
          page_count: res.page_count ?? res.pages,
          language_hint: res.language_hint,
          status: res.status || "ready",
        },
      ]);
      setActiveDocId(res.doc_id);
      if (typeof window !== "undefined" && window.innerWidth >= 1100) {
        setActiveTab("split");
      } else {
        setActiveTab("document");
      }
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDeleteDoc = useCallback(
    async (docId: string) => {
      try {
        await deleteDocument(docId);
        setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
        if (activeDocId === docId) {
          setActiveDocId(null);
          setViewerData({ docId: null, pages: [] });
          setSelectedText("");
          setSearchQuery("");
          setSearchResults([]);
          setActiveTab("explain");
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    },
    [activeDocId]
  );

  // ── Text selected in viewer → offer to explain ──────────────────────
  const handleTextHighlight = useCallback((text: string) => {
    setSelectedText(text);
  }, []);

  // ── Citation click → jump to page + highlight evidence ─────────────
  const handleCitationClick = useCallback((citation: Citation) => {
    if (typeof window !== "undefined" && window.innerWidth >= 1100) {
      setActiveTab("split");
    } else {
      setActiveTab("document");
    }
    setHighlightPage(citation.page);
    setActiveSearchMatchIdx(null);
    // Wait for the document panel to render/mount, then scroll smoothly
    setTimeout(() => {
      const pageEl = document.getElementById(`page-${citation.page}`);
      pageEl?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  }, []);

  // ── Search match click → jump to that match ────────────────────────
  const handleSearchMatchClick = useCallback((idx: number) => {
    setActiveSearchMatchIdx(idx);
    const page = searchResults[idx]?.page;
    if (page) {
      setTimeout(() => {
        document
          .getElementById(`page-${page}`)
          ?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 60);
    }
  }, [searchResults]);

  const goToMatch = useCallback((idx: number | null) => {
    setActiveSearchMatchIdx(idx);
  }, []);

  // ── Clear highlights ────────────────────────────────────────────────
  const clearHighlights = useCallback(() => {
    setHighlightPage(null);
    setSelectedText("");
    setActiveSearchMatchIdx(null);
  }, []);

  // ── Page jump ───────────────────────────────────────────────────────
  const jumpToPage = useCallback((pageNum: number) => {
    setHighlightPage(null);
    document
      .getElementById(`page-${pageNum}`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  // ── Action extraction (PR-009): from pasted text or active document ──
  const handleExtractActions = useCallback(() => {
    if (actionsLoading) return;
    const sourceText = inputText.trim();
    if (!sourceText && !activeDocId) return;
    setActionsLoading(true);
    setActionsError(null);
    extractActions(sourceText || undefined, sourceText ? undefined : activeDocId || undefined, question.trim() || undefined)
      .then(setActions)
      .catch((e) =>
        setActionsError(e instanceof Error ? e.message : String(e))
      )
      .finally(() => setActionsLoading(false));
  }, [actionsLoading, inputText, activeDocId, question]);

  // ── Submit a thumbs up/down rating for the current explanation ─────────
  const handleFeedback = useCallback(
    async (rating: number) => {
      if (!explanation || feedback.confirmed) return;
      try {
        const res = await submitFeedback(
          explanation.explanation.question,
          rating,
          activeDocId || undefined
        );
        setFeedback({
          rating,
          confirmed: true,
          aggregate: res.aggregate,
        });
      } catch {
        // Feedback is best-effort; never block the UX on it.
      }
    },
    [explanation, activeDocId, feedback.confirmed]
  );

  // Keyboard shortcut: Ctrl+Enter → explain ────────────────────────
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleExplain();
      }
    },
    [handleExplain]
  );

  const activeDoc = documents.find((d) => d.doc_id === activeDocId);
  const processingStatus = loading
    ? activeDocId
      ? "Analyzing document and verifying citations..."
      : "Analyzing text and generating verified explanation..."
    : "";

  return (
    <div style={styles.wrap}>
      {/* Universal document file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
        style={{ display: "none" }}
        onChange={handleFileSelect}
        id="doc-upload"
      />

      {/* ── Header ──────────────────────────────────────────────────── */}
      <header className="glass-header" style={styles.header}>
        <div style={styles.headerInner}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            <Link href="/" style={styles.brand} aria-label="hamiGenZ home">
              <svg width="28" height="28" viewBox="0 0 32 32" fill="none" aria-hidden="true">
                <rect width="32" height="32" rx="7" fill="#c8520b" />
                <path d="M9 10h14M9 16h14M9 22h10" stroke="white" strokeWidth="2" strokeLinecap="round" />
                <circle cx="24" cy="22" r="3.5" fill="white" fillOpacity="0.9" />
              </svg>
              <span style={styles.brandName}>hamiGenZ</span>
            </Link>
            <span className="ws-header-badge" style={styles.headerBadge}>Civic Doc Intel</span>
          </div>

          <nav className="ws-tab-nav" style={styles.tabs} aria-label="Workspace mode">
            <button
              style={{ ...styles.tab, ...(activeTab === "explain" ? styles.tabActive : {}) }}
              onClick={() => setActiveTab("explain")}
              aria-pressed={activeTab === "explain"}
            >
              Understand text
            </button>
            <button
              style={{ ...styles.tab, ...(activeTab === "split" ? styles.tabActive : {}) }}
              onClick={() => setActiveTab("split")}
              aria-pressed={activeTab === "split"}
              title="Split view: Input, Answer, and Evidence side-by-side"
            >
              Split View
            </button>
            <button
              style={{ ...styles.tab, ...(activeTab === "document" ? styles.tabActive : {}) }}
              onClick={() => setActiveTab("document")}
              aria-pressed={activeTab === "document"}
            >
              Document reader
            </button>
          </nav>

          <div style={styles.headerActions}>
            {activeDoc && (
              <div className="ws-header-doc-chip" style={styles.headerDocChip} title={activeDoc.filename}>
                <span>📄</span>
                <span style={styles.headerDocName}>{activeDoc.filename}</span>
              </div>
            )}
            <button
              type="button"
              style={styles.headerUploadBtn}
              onClick={() => fileInputRef.current?.click()}
              aria-label="Upload document"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <span>Upload Doc</span>
            </button>
          </div>
        </div>
      </header>

      {/* ── Main panel ───────────────────────────────────────────────── */}
      <main style={styles.main}>
        {(activeTab === "explain" || activeTab === "split") && (
          <div
            className={activeTab === "split" ? "ws-grid-split" : "ws-grid-2"}
            style={activeTab === "split" ? styles.splitLayout : styles.explainLayout}
          >
            {/* Left: input panel */}
            <div className="glass-card" style={{ ...styles.inputPanel, padding: "var(--space-6)", borderRadius: "var(--radius-xl)" }}>
              <div style={styles.panelHeader}>
                <h2 style={styles.panelTitle}>What do you want to understand?</h2>
                <p style={styles.panelSubtitle}>
                  Paste difficult Nepali, formal text, or a document excerpt.
                </p>
              </div>

              {activeDocId && (
                <div style={styles.docBadge}>
                  <span style={styles.docBadgeLabel}>Active document:</span>
                  <span style={styles.docBadgeName}>{activeDoc?.filename}</span>
                  <button
                    style={styles.docBadgeClear}
                    onClick={() => {
                      setActiveDocId(null);
                      setViewerData({ docId: null, pages: [] });
                      setSelectedText("");
                      setSearchQuery("");
                      setSearchResults([]);
                      setActiveSearchMatchIdx(null);
                    }}
                    title="Switch to direct text"
                    aria-label="Clear active document"
                  >
                    ×
                  </button>
                </div>
              )}

              {/* Explanation level selector */}
              <div style={styles.row}>
                <span style={styles.rowLabel}>Explain as:</span>
                <ExplanationLevelSelect value={explainLevel} onChange={setExplainLevel} />
              </div>

              {/* Target language */}
              <div style={styles.row}>
                <label style={styles.rowLabel} htmlFor="target-lang">
                  Answer in:
                </label>
                <select
                  id="target-lang"
                  style={styles.select}
                  value={targetLang}
                  onChange={(e) => setTargetLang(e.target.value as TargetLang)}
                >
                  <option value="auto">Auto-detect</option>
                  <option value="nepali">Nepali</option>
                  <option value="english">English</option>
                  <option value="romanized_nepali">Romanized Nepali</option>
                </select>
              </div>

              {/* Text input */}
              <textarea
                style={styles.textarea}
                placeholder="Paste difficult text here..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={8}
                aria-label="Text to explain"
              />

              {/* Clickable examples (empty-state teaching) */}
              {!inputText && (
                <div style={styles.examplesRow}>
                  {EXAMPLE_PROMPTS.map((ex) => (
                    <button
                      key={ex.text}
                      style={{
                        ...styles.exampleChip,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "var(--space-2)",
                        boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                      }}
                      onClick={() => setInputText(ex.text)}
                    >
                      <span style={{ fontSize: "11px", opacity: 0.9 }}>{ex.tag}</span>
                      <span>{ex.text}</span>
                    </button>
                  ))}
                </div>
              )}

              {selectedText && (
                <div style={styles.selectedSource}>
                  <span style={styles.selectedSourceLabel}>
                    Selected from document: “{selectedText.slice(0, 60)}
                    {selectedText.length > 60 ? "…" : ""}”
                  </span>
                  <button
                    style={styles.selectedSourceClear}
                    onClick={() => {
                      setSelectedText("");
                      setInputText("");
                    }}
                  >
                    Clear selection
                  </button>
                </div>
              )}

              {/* Optional question */}
              <input
                style={styles.questionInput}
                placeholder="Optional: ask a specific question..."
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                aria-label="Optional question"
              />

              {/* Action buttons */}
              <div style={styles.actions}>
                <button
                  style={{
                    ...styles.explainBtn,
                    ...(loading || !inputText.trim() ? styles.explainBtnDisabled : {}),
                  }}
                  disabled={loading || !inputText.trim()}
                  onClick={handleExplain}
                >
                  {loading ? <span style={styles.spinner} aria-hidden="true" /> : "Understand"}
                </button>
                <button
                  style={styles.clearBtn}
                  onClick={() => {
                    setInputText("");
                    setQuestion("");
                    setExplanation(null);
                    setError(null);
                    setSelectedText("");
                    setFeedback({ rating: null, confirmed: false, aggregate: null });
                  }}
                >
                  Clear
                </button>
              </div>

              <div aria-live="polite">
                {loading && processingStatus && (
                  <p style={styles.loadingHint}>{processingStatus}</p>
                )}
              </div>

              {error && (
                <div style={styles.errorAlert} role="alert">
                  <div style={{ display: "flex", alignItems: "flex-start", gap: "var(--space-3)" }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#b91c1c" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: "2px" }} aria-hidden="true">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                    <div style={{ flex: 1 }}>
                      <span style={{ display: "block", fontSize: "var(--text-xs)", fontWeight: "var(--font-semibold)", color: "#991b1b", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "2px" }}>
                        Understanding Error
                      </span>
                      <p style={{ margin: "0 0 var(--space-2) 0", fontSize: "var(--text-sm)", color: "#7f1d1d" }}>{error}</p>
                      <div style={{ display: "flex", gap: "var(--space-2)" }}>
                        <button
                          type="button"
                          style={styles.errorRetryBtn}
                          onClick={handleExplain}
                        >
                          Try again
                        </button>
                        <button
                          type="button"
                          style={styles.errorDismissBtn}
                          onClick={() => setError(null)}
                        >
                          Dismiss
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Action layer: what should I do? (from pasted text) */}
              <ActionPanel
                actions={actions}
                loading={actionsLoading}
                error={actionsError}
                onExtract={handleExtractActions}
                disabled={!inputText.trim() && !activeDocId}
              />

              {/* Form understanding: explain form fields (PR-010) */}
              <FormPanel
                text={inputText.trim() || undefined}
                docId={activeDocId}
                targetLang={targetLang}
              />

              <p style={styles.hint}>
                Ctrl+Enter to explain · Select text in the Document tab to explain it
              </p>
            </div>

            {/* Right: explanation output */}
            <div className="glass-card" style={{ ...styles.outputPanel, padding: "var(--space-6)", borderRadius: "var(--radius-xl)" }}>
              {loading ? (
                <div style={styles.loadingSkeletonContainer} aria-live="polite">
                  <div style={styles.skeletonStageBadge}>
                    <span className="ws-spin" style={styles.skeletonPulseDot} />
                    <span>{processingStatus || "Analyzing Nepal document..."}</span>
                  </div>
                  <div className="skeleton-shimmer" style={{ width: "45%", height: "24px", marginBottom: "var(--space-4)" }} />
                  <div className="skeleton-shimmer" style={{ width: "100%", height: "14px", marginBottom: "var(--space-2)" }} />
                  <div className="skeleton-shimmer" style={{ width: "94%", height: "14px", marginBottom: "var(--space-2)" }} />
                  <div className="skeleton-shimmer" style={{ width: "82%", height: "14px", marginBottom: "var(--space-5)" }} />

                  <div className="skeleton-shimmer" style={{ width: "35%", height: "18px", marginBottom: "var(--space-3)" }} />
                  <div className="skeleton-shimmer" style={{ width: "98%", height: "14px", marginBottom: "var(--space-2)" }} />
                  <div className="skeleton-shimmer" style={{ width: "89%", height: "14px", marginBottom: "var(--space-5)" }} />

                  <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-3)" }}>
                    <div className="skeleton-shimmer" style={{ width: "100px", height: "34px", borderRadius: "var(--radius-full)" }} />
                    <div className="skeleton-shimmer" style={{ width: "120px", height: "34px", borderRadius: "var(--radius-full)" }} />
                  </div>
                </div>
              ) : !explanation ? (
                <div style={styles.emptyState}>
                  <div style={styles.emptyHeader}>
                    <div style={styles.emptyIcon}>
                      <svg width="40" height="40" viewBox="0 0 32 32" fill="none" aria-hidden="true">
                        <rect width="32" height="32" rx="8" fill="#c8520b" fillOpacity="0.12" />
                        <path
                          d="M9 10h14M9 16h14M9 22h10"
                          stroke="#c8520b"
                          strokeWidth="2"
                          strokeLinecap="round"
                        />
                        <circle cx="24" cy="22" r="3.5" fill="#c8520b" />
                      </svg>
                    </div>
                    <div>
                      <h3 style={styles.emptyTitle}>Understand Any Nepali Notice or Document</h3>
                      <p style={styles.emptySubtitle}>
                        Clear, plain-language answers with page citations and official source verification.
                      </p>
                    </div>
                  </div>

                  {/* Interactive preview card showing Nepal civic intelligence */}
                  <div style={styles.emptyPreviewCard}>
                    <div style={styles.emptyPreviewHeader}>
                      <span style={styles.emptyPreviewBadge}>नमुना उदाहरण (Sample Notice)</span>
                      <span style={styles.emptyPreviewSource}>राहदानी विभाग · परिपत्र</span>
                    </div>
                    <p style={styles.emptyPreviewText}>
                      “नेपाल सरकार राहदानी विभागको निर्णयानुसार विद्युतीय राहदानी (e-Passport) आवेदन गर्दा राष्ट्रिय परिचयपत्र नम्बर अनिवार्य गरिएको छ…”
                    </p>
                    <div style={styles.emptyPreviewAnswer}>
                      <span style={styles.emptyPreviewAnswerTag}>hamiGenZ सरल बुझाई:</span>
                      <p style={styles.emptyPreviewAnswerText}>
                        नयाँ राहदानी बनाउँदा वा रिन्यु गर्दा राष्ट्रिय परिचयपत्र (NID) नम्बर अनिवार्य चाहिन्छ। सक्कल नागरिकता साथमै लैजानुहोस्।
                      </p>
                    </div>
                    <div style={styles.emptyPreviewFooter}>
                      <span style={styles.emptyPreviewCitation}>📄 Page 1 · Verified Evidence</span>
                      <span style={styles.emptyPreviewProvenance}>🏛️ Department of Passports</span>
                    </div>
                  </div>

                  {/* Clickable prompt suggestions */}
                  <div style={styles.emptyPromptsSection}>
                    <span style={styles.emptyPromptsLabel}>Try with a single click:</span>
                    <div style={styles.emptyPromptsList}>
                      <button
                        type="button"
                        style={styles.emptyPromptBtn}
                        onClick={() => {
                          setInputText("राहदानी नवीकरण गर्दा राष्ट्रिय परिचयपत्र (NID) नम्बर अनिवार्य गरिएको सूचनाको अर्थ के हो?");
                          setQuestion("के के कागजात चाहिन्छ?");
                        }}
                      >
                        <span>🛂 राहदानी नवीकरण नियम</span>
                      </button>
                      <button
                        type="button"
                        style={styles.emptyPromptBtn}
                        onClick={() => {
                          setInputText("वडा कार्यालयबाट नागरिकताको प्रतिलिपि सिफारिस लिने कार्यविधि र आवश्यक दस्तुर के कति हो?");
                          setQuestion("कहाँ निवेदन दिने?");
                        }}
                      >
                        <span>🏛️ नागरिकता प्रतिलिपि सिफारिस</span>
                      </button>
                      <button
                        type="button"
                        style={styles.emptyPromptBtn}
                        onClick={() => {
                          setInputText("मालपोत कार्यालयमा जग्गा रजिष्ट्रेशन लिखत पारित गर्दा लाग्ने सेवा शुल्क र आवश्यक कागजातहरुको सूची।");
                        }}
                      >
                        <span>📋 मालपोत लिखत कागजात</span>
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  <ExplanationPanel
                    explanation={explanation}
                    onCitationClick={handleCitationClick}
                    activeCitation={highlightPage}
                    onClearCitation={clearHighlights}
                    docId={activeDocId || undefined}
                    sourceUnavailable={
                      !explanation.citations?.length && explanation.provenance !== "general_ai"
                    }
                  />
                  {/* User feedback: thumbs up / thumbs down on the explanation */}
                  {explanation && (
                    <div style={styles.feedbackRow}>
                      <span style={styles.feedbackLabel}>
                        Was this helpful?
                      </span>
                      {!feedback.confirmed ? (
                        <div style={styles.feedbackBtns}>
                          <button
                            style={{
                              ...styles.feedbackBtn,
                              ...(feedback.rating === 1 ? styles.feedbackBtnActive : {}),
                            }}
                            onClick={() => handleFeedback(1)}
                            aria-label="Thumbs up (helpful)"
                            title="Helpful"
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                              <path d="M7 10v12" />
                              <path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.5L12 4.12A2 2 0 0 1 15 5.88z" />
                            </svg>
                          </button>
                          <button
                            style={{
                              ...styles.feedbackBtn,
                              ...(feedback.rating === -1 ? styles.feedbackBtnActive : {}),
                            }}
                            onClick={() => handleFeedback(-1)}
                            aria-label="Thumbs down (not helpful)"
                            title="Not helpful"
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                              <path d="M17 14V2" />
                              <path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.5L12 19.88A2 2 0 0 1 9 18.12z" />
                            </svg>
                          </button>
                        </div>
                      ) : (
                        <div style={styles.feedbackConfirmed}>
                          <span style={styles.feedbackConfirmedIcon}>
                            {feedback.rating === 1 ? "👍" : "👎"}
                          </span>
                          <span style={styles.feedbackConfirmedText}>
                            Thanks — your rating helps hamiGenZ get better.
                          </span>
                          {feedback.aggregate && (
                            <span style={styles.feedbackAggregate}>
                              So far: {feedback.aggregate.up} helpful /
                              {feedback.aggregate.down} not helpful
                              {feedback.aggregate.up_rate !== null
                                ? ` (${Math.round(feedback.aggregate.up_rate * 100)}% helpful)`
                                : ""}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Third Column: Document Companion in Split View */}
            {activeTab === "split" && (
              <div style={styles.docViewerPanel}>
                {!activeDocId ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)", height: "100%" }}>
                    <div style={styles.emptyState}>
                      <div style={styles.uploadIconCircle}>
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                          <polyline points="14 2 14 8 20 8" />
                          <line x1="16" y1="13" x2="8" y2="13" />
                          <line x1="16" y1="17" x2="8" y2="17" />
                          <polyline points="10 9 9 9 8 9" />
                        </svg>
                      </div>
                      <h3 style={styles.emptyTitle}>Document Companion</h3>
                      <p style={styles.emptySubtitle}>
                        Upload or select a Nepal document to inspect citation evidence side-by-side with your explanation.
                      </p>
                    </div>

                    <div
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                      style={{
                        ...styles.uploadDropZone,
                        ...(isDragging ? styles.uploadDropZoneActive : {}),
                      }}
                    >
                      <label style={{ ...styles.uploadLabel, border: "none", padding: 0 }} htmlFor="doc-upload">
                        <span style={styles.uploadTitle}>
                          {isDragging ? "Drop your Nepal document here" : "Upload document (PDF, image)"}
                        </span>
                        <span style={styles.uploadSubtitle}>PDF, PNG, JPG up to 20MB</span>
                        <span style={styles.uploadBrowseBtn}>Choose file</span>
                      </label>
                    </div>

                    {documents.length > 0 && (
                      <div style={{ marginTop: "var(--space-2)" }}>
                        <span style={{ fontSize: "11px", fontWeight: "var(--font-semibold)", color: "var(--color-text-tertiary)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: "var(--space-2)" }}>
                          Or open an existing document:
                        </span>
                        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)", maxHeight: "220px", overflowY: "auto" }}>
                          {documents.map((d) => (
                            <button
                              key={d.doc_id}
                              type="button"
                              style={{
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "space-between",
                                padding: "8px 12px",
                                background: "var(--color-surface)",
                                border: "1px solid var(--color-border)",
                                borderRadius: "var(--radius-md)",
                                cursor: "pointer",
                                textAlign: "left",
                                fontSize: "var(--text-xs)",
                              }}
                              onClick={() => {
                                setActiveDocId(d.doc_id);
                                clearHighlights();
                              }}
                            >
                              <span style={{ fontWeight: "var(--font-medium)", color: "var(--color-text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                {d.filename}
                              </span>
                              <span style={{ color: "var(--color-accent)", fontWeight: "var(--font-semibold)", whiteSpace: "nowrap", marginLeft: "var(--space-2)" }}>
                                Open →
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : viewerLoading ? (
                  <div style={styles.emptyState}>
                    <p style={styles.emptySubtitle}>Loading document viewer...</p>
                  </div>
                ) : (
                  <>
                    <div style={styles.viewerToolbar}>
                      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", minWidth: 0, flex: 1 }}>
                        <span style={styles.pageNavLabel}>
                          {viewerPages.length} page{viewerPages.length !== 1 ? "s" : ""} · {activeDoc?.filename}
                        </span>
                        <button
                          type="button"
                          style={{
                            padding: "2px 8px",
                            background: "var(--color-bg-alt)",
                            border: "1px solid var(--color-border)",
                            borderRadius: "var(--radius-sm)",
                            fontSize: "11px",
                            color: "var(--color-text-secondary)",
                            cursor: "pointer",
                            whiteSpace: "nowrap",
                          }}
                          onClick={() => setActiveTab("document")}
                          title="Open full reader view"
                        >
                          Full reader ↗
                        </button>
                      </div>
                      <div style={styles.viewerToolbarRight}>
                        {viewerPages.length > 1 && (
                          <select
                            style={styles.select}
                            value=""
                            onChange={(e) => {
                              const n = Number(e.target.value);
                              if (n) jumpToPage(n);
                            }}
                            aria-label="Jump to page"
                          >
                            <option value="">Page…</option>
                            {viewerPages.map((p) => (
                              <option key={p.page_num} value={p.page_num}>
                                Page {p.page_num}
                              </option>
                            ))}
                          </select>
                        )}
                        {(highlightPage || selectedText || activeSearchMatchIdx !== null) && (
                          <button style={styles.pageNavBtn} onClick={clearHighlights}>
                            Clear
                          </button>
                        )}
                      </div>
                    </div>

                    <div style={styles.viewerScroll}>
                      <DocumentViewer
                        docId={activeDocId}
                        pages={viewerPages}
                        onTextHighlight={handleTextHighlight}
                        citationsByPage={citationsByPage}
                        searchMatches={searchResults}
                        activeCitationPage={highlightPage}
                        activeSearchMatchIdx={activeSearchMatchIdx}
                        onActiveSearchMatchChange={goToMatch}
                      />
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === "document" && (
          <div className="ws-grid-3" style={styles.docLayout}>
            {/* Left: document list + upload */}
            <div style={styles.docListPanel}>
              <div style={styles.panelHeader}>
                <h2 style={styles.panelTitle}>Your Documents</h2>
              </div>

              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                style={{
                  ...styles.uploadDropZone,
                  ...(isDragging ? styles.uploadDropZoneActive : {}),
                }}
              >
                <label style={{ ...styles.uploadLabel, border: "none", padding: 0 }} htmlFor="doc-upload">
                  <div style={styles.uploadIconCircle}>
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="17 8 12 3 7 8" />
                      <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                  </div>
                  <span style={styles.uploadTitle}>
                    {isDragging ? "Drop your Nepal document here" : "Upload document (PDF, image)"}
                  </span>
                  <span style={styles.uploadSubtitle}>PDF, PNG, JPG, or TIFF up to 20MB</span>
                </label>
              </div>

              {documents.length === 0 ? (
                <div style={styles.noDocs}>
                  <p>No documents yet.</p>
                  <p>Upload a PDF or image to get started.</p>
                </div>
              ) : (
                <div style={styles.docList}>
                  {documents.map((doc) => (
                    <div
                      key={doc.doc_id}
                      style={{
                        ...styles.docItem,
                        ...(activeDocId === doc.doc_id ? styles.docItemActive : {}),
                      }}
                    >
                      <div style={styles.docItemInfo}>
                        <span style={styles.docItemName}>{doc.filename}</span>
                        <span style={styles.docItemMeta}>
                          {doc.page_count != null ? `${doc.page_count} pages` : "pages unknown"}
                        </span>
                      </div>
                      <div style={styles.docItemActions}>
                        <button
                          style={styles.docItemOpen}
                          onClick={() => {
                            setActiveDocId(doc.doc_id);
                            clearHighlights();
                          }}
                        >
                          {activeDocId === doc.doc_id ? "Viewing" : "Open"}
                        </button>
                        <button
                          style={styles.docItemDelete}
                          onClick={() => handleDeleteDoc(doc.doc_id)}
                          aria-label={`Delete ${doc.filename}`}
                          title="Delete document"
                        >
                          ×
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Provenance note for last explanation */}
              {explanation && (
                <div style={styles.sideSection}>
                  <ProvenanceBadge
                    provenance={explanation.provenance}
                    grounding={explanation.grounding}
                    sourceUnavailable={
                      !explanation.citations?.length && explanation.provenance !== "general_ai"
                    }
                  />
                </div>
              )}
            </div>

            {/* Center: document viewer */}
            <div style={styles.docViewerPanel}>
              {!activeDocId ? (
                <div style={styles.emptyState}>
                  <h3 style={styles.emptyTitle}>Select a document</h3>
                  <p style={styles.emptySubtitle}>
                    Upload or select a document from the left panel to view its pages and
                    extracted text.
                  </p>
                </div>
              ) : viewerLoading ? (
                <div style={styles.emptyState}>
                  <p style={styles.emptySubtitle}>Loading document viewer...</p>
                </div>
              ) : (
                <>
                  <div style={styles.viewerToolbar}>
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", minWidth: 0, flex: 1 }}>
                      <span style={styles.pageNavLabel}>
                        {viewerPages.length} page{viewerPages.length !== 1 ? "s" : ""}
                        {activeDoc ? ` · ${activeDoc.filename}` : ""}
                      </span>
                      {explanation && (
                        <button
                          type="button"
                          style={styles.returnToExplainBtn}
                          onClick={() => setActiveTab(typeof window !== "undefined" && window.innerWidth >= 1100 ? "split" : "explain")}
                          title="Return to explanation"
                        >
                          ← Return to explanation
                        </button>
                      )}
                    </div>
                    <div style={styles.viewerToolbarRight}>
                      {viewerPages.length > 1 && (
                        <select
                          style={styles.select}
                          value=""
                          onChange={(e) => {
                            const n = Number(e.target.value);
                            if (n) jumpToPage(n);
                          }}
                          aria-label="Jump to page"
                        >
                          <option value="">Jump to page…</option>
                          {viewerPages.map((p) => (
                            <option key={p.page_num} value={p.page_num}>
                              Page {p.page_num}
                            </option>
                          ))}
                        </select>
                      )}
                      {(highlightPage || selectedText || activeSearchMatchIdx !== null) && (
                        <button style={styles.pageNavBtn} onClick={clearHighlights}>
                          Clear highlights
                        </button>
                      )}
                    </div>
                  </div>

                  <div style={styles.viewerScroll}>
                    <DocumentViewer
                      docId={activeDocId}
                      pages={viewerPages}
                      onTextHighlight={handleTextHighlight}
                      citationsByPage={citationsByPage}
                      searchMatches={searchResults}
                      activeCitationPage={highlightPage}
                      activeSearchMatchIdx={activeSearchMatchIdx}
                      onActiveSearchMatchChange={goToMatch}
                    />
                  </div>
                </>
              )}
            </div>

            {/* Right: search + selected text explain */}
            <div style={styles.docSidePanel}>
              <div style={styles.sideSection}>
                <h3 style={styles.sideTitle}>Search document</h3>
                <div style={styles.searchRow}>
                  <input
                    style={styles.searchInput}
                    placeholder="Search text..."
                    value={searchQuery}
                    onChange={(e) => {
                      const q = e.target.value;
                      setSearchQuery(q);
                      if (!q.trim()) {
                        setSearchResults([]);
                        setActiveSearchMatchIdx(null);
                      }
                    }}
                    aria-label="Search document text"
                  />
                  {searchQuery && (
                    <button
                      style={styles.searchClear}
                      onClick={() => {
                        setSearchQuery("");
                        setSearchResults([]);
                        setActiveSearchMatchIdx(null);
                      }}
                    >
                      Clear
                    </button>
                  )}
                </div>
                {searchQuery.trim() !== "" && searchResults.length === 0 && (
                  <div style={styles.searchNoResults}>
                    No matches found for “{searchQuery}”
                  </div>
                )}
                {searchResults.length > 0 && (
                  <>
                    <div style={styles.searchResultsInfo}>
                      <span style={styles.searchResultsCount}>
                        {searchResults.length} match{searchResults.length !== 1 ? "es" : ""}
                      </span>
                    </div>
                    <div style={styles.searchResults}>
                      {searchResults.map((m, i) => (
                        <button
                          key={i}
                          style={{
                            ...styles.searchMatch,
                            ...(activeSearchMatchIdx === i ? styles.searchMatchActive : {}),
                          }}
                          onClick={() => handleSearchMatchClick(i)}
                        >
                          <span style={styles.searchMatchPage}>Page {m.page}</span>
                          <span style={styles.searchMatchText}>
                            {m.text.slice(0, 120)}…
                          </span>
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>

              {/* Action layer for the active document (PR-009) */}
              <ActionPanel
                actions={actions}
                loading={actionsLoading}
                error={actionsError}
                onExtract={handleExtractActions}
                disabled={!activeDocId}
              />

              {/* Form understanding for the active document (PR-010) */}
              <FormPanel docId={activeDocId} targetLang={targetLang} />

              <div style={styles.sideSection}>
                <h3 style={styles.sideTitle}>Explain selected text</h3>
                {selectedText ? (
                  <div style={styles.selectedBox}>
                    <div style={styles.selectedTextQuoted}>
                      “{selectedText.slice(0, 200)}
                      {selectedText.length > 200 ? "…" : ""}”
                    </div>
                    <button
                      style={styles.explainSelectedBtn}
                      onClick={() => explainFromSelection(selectedText)}
                      disabled={loading}
                    >
                      Explain this
                    </button>
                  </div>
                ) : (
                  <p style={styles.sideHint}>
                    Highlight text in the document viewer, then explain it in Simple,
                    Very Simple, or Original style.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer style={styles.footer}>
        <span style={styles.footerBrand}>hamiGenZ</span>
        <span style={styles.footerTagline}>Don&apos;t understand it? Ask hamiGenZ.</span>
      </footer>
    </div>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────
const styles: Record<string, React.CSSProperties> = {
  wrap: {
    display: "flex",
    flexDirection: "column",
    minHeight: "100vh",
    background: "var(--color-bg)",
    fontFamily: "var(--font-sans)",
  },
  header: {
    borderBottom: "1px solid var(--color-border)",
    background: "var(--color-surface)",
  },
  headerInner: {
    maxWidth: "1440px",
    margin: "0 auto",
    padding: "var(--space-3) var(--space-6)",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "var(--space-3)",
    minHeight: "56px",
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-2)",
    textDecoration: "none",
  },
  brandName: {
    fontWeight: "var(--font-bold)",
    fontSize: "var(--text-lg)",
    color: "#c8520b",
    letterSpacing: "-0.02em",
    whiteSpace: "nowrap",
  },
  tabs: {
    display: "flex",
    gap: "var(--space-1)",
    background: "var(--color-bg-alt)",
    borderRadius: "var(--radius-md)",
    padding: "2px",
  },
  tab: {
    padding: "var(--space-2) var(--space-4)",
    border: "none",
    background: "transparent",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-text-secondary)",
    cursor: "pointer",
    transition: "background-color var(--duration-fast) var(--ease-default), color var(--duration-fast) var(--ease-default)",
  },
  tabActive: {
    background: "var(--color-accent)",
    color: "white",
  },
  headerDesc: {
    fontSize: "var(--text-sm)",
    color: "var(--color-text-tertiary)",
    textAlign: "center",
    paddingBottom: "var(--space-2)",
  },
  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
  },

  // ── Explain layout ──────────────────────────────────────────────────
  explainLayout: {
    flex: 1,
    maxWidth: "1200px",
    margin: "0 auto",
    width: "100%",
    padding: "var(--space-6)",
  },
  inputPanel: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-4)",
  },
  outputPanel: {
    display: "flex",
    flexDirection: "column",
    minHeight: "400px",
  },
  panelHeader: {
    marginBottom: "var(--space-2)",
  },
  panelTitle: {
    fontSize: "var(--text-xl)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-primary)",
    margin: 0,
  },
  panelSubtitle: {
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
    margin: "var(--space-1) 0 0 0",
  },

  // ── Document badge ──────────────────────────────────────────────────
  docBadge: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-2)",
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-accent-soft)",
    border: "1px solid #fed7aa",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    color: "var(--color-accent)",
    width: "fit-content",
    maxWidth: "100%",
  },
  docBadgeLabel: {
    fontWeight: "var(--font-medium)",
    whiteSpace: "nowrap",
  },
  docBadgeName: {
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  docBadgeClear: {
    background: "none",
    border: "none",
    color: "var(--color-accent)",
    cursor: "pointer",
    fontSize: "var(--text-lg)",
    padding: "0 2px",
    lineHeight: 1,
  },
  selectedSource: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "var(--space-3)",
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-evidence)",
    border: "1px solid var(--color-evidence-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-xs)",
    color: "var(--color-info)",
  },
  selectedSourceLabel: {
    fontWeight: "var(--font-medium)",
    flex: 1,
    minWidth: 0,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  selectedSourceClear: {
    background: "none",
    border: "1px solid var(--color-evidence-border)",
    color: "var(--color-info)",
    borderRadius: "var(--radius-sm)",
    padding: "2px 8px",
    fontSize: "var(--text-xs)",
    cursor: "pointer",
    whiteSpace: "nowrap",
  },

  // ── Rows / selects ──────────────────────────────────────────────────
  row: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-3)",
    flexWrap: "wrap",
  },
  rowLabel: {
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-text-secondary)",
    whiteSpace: "nowrap",
  },
  select: {
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-primary)",
    cursor: "pointer",
  },

  // ── Inputs ──────────────────────────────────────────────────────────
  textarea: {
    width: "100%",
    padding: "var(--space-4)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-lg)",
    fontSize: "var(--text-base)",
    lineHeight: 1.6,
    color: "var(--color-text-primary)",
    resize: "vertical",
    fontFamily: "var(--font-sans)",
  },
  questionInput: {
    width: "100%",
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-bg-alt)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-primary)",
  },
  examplesRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: "var(--space-2)",
  },
  exampleChip: {
    padding: "var(--space-1) var(--space-3)",
    background: "var(--color-bg-alt)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-full)",
    fontSize: "var(--text-xs)",
    color: "var(--color-text-secondary)",
    cursor: "pointer",
    transition: "background-color var(--duration-fast) var(--ease-default), border-color var(--duration-fast) var(--ease-default), color var(--duration-fast) var(--ease-default)",
  },

  // ── Actions ─────────────────────────────────────────────────────────
  actions: {
    display: "flex",
    gap: "var(--space-2)",
  },
  explainBtn: {
    flex: 1,
    padding: "var(--space-3) var(--space-6)",
    background: "var(--color-accent)",
    color: "white",
    border: "none",
    borderRadius: "var(--radius-lg)",
    fontSize: "var(--text-base)",
    fontWeight: "var(--font-semibold)",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "var(--space-2)",
    transition: "background 0.15s ease",
  },
  explainBtnDisabled: {
    opacity: 0.6,
    cursor: "wait",
  },
  clearBtn: {
    padding: "var(--space-3) var(--space-4)",
    background: "var(--color-surface)",
    color: "var(--color-text-secondary)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-lg)",
    fontSize: "var(--text-sm)",
    cursor: "pointer",
  },
  spinner: {
    width: "16px",
    height: "16px",
    border: "2px solid rgba(255,255,255,0.3)",
    borderTopColor: "white",
    borderRadius: "50%",
    display: "inline-block",
    animation: "ws-spin 0.6s linear infinite",
  },
  errorBox: {
    padding: "var(--space-3)",
    background: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    color: "#991b1b",
    wordBreak: "break-word",
  },
  loadingHint: {
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-info)",
    background: "var(--color-evidence)",
    padding: "6px 10px",
    borderRadius: "var(--radius-md)",
    textAlign: "center",
    margin: "0",
  },
  hint: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
    textAlign: "center",
    margin: 0,
  },

  // ── Empty state ─────────────────────────────────────────────────────
  emptyState: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    padding: "var(--space-8)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-xl)",
    gap: "var(--space-3)",
  },
  emptyIcon: {
    marginBottom: "var(--space-2)",
  },
  emptyTitle: {
    fontSize: "var(--text-lg)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-primary)",
    margin: 0,
  },
  emptySubtitle: {
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
    margin: 0,
    maxWidth: "300px",
  },
  emptyLevels: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
    width: "100%",
    maxWidth: "320px",
    marginTop: "var(--space-4)",
  },
  emptyLevel: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-3)",
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-bg-alt)",
    borderRadius: "var(--radius-md)",
  },
  emptyLevelBadge: {
    padding: "2px 8px",
    background: "var(--color-accent)",
    color: "white",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-semibold)",
    whiteSpace: "nowrap",
  },
  emptyLevelDesc: {
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
    flex: 1,
    textAlign: "left",
  },

  // ── Document layout ──────────────────────────────────────────────────
  docLayout: {
    flex: 1,
    maxWidth: "1400px",
    margin: "0 auto",
    width: "100%",
    padding: "var(--space-6)",
    minHeight: "500px",
  },
  docListPanel: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-4)",
    minWidth: 0,
  },
  uploadLabel: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "var(--space-2)",
    padding: "var(--space-4)",
    background: "var(--color-surface)",
    border: "1px dashed var(--color-border)",
    borderRadius: "var(--radius-lg)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
    cursor: "pointer",
    textAlign: "center",
    transition: "background-color var(--duration-fast) var(--ease-default), border-color var(--duration-fast) var(--ease-default), color var(--duration-fast) var(--ease-default)",
  },
  noDocs: {
    padding: "var(--space-6)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-lg)",
    textAlign: "center",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
  },
  docList: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
    overflowY: "auto",
    maxHeight: "400px",
  },
  docItem: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "var(--space-3)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    gap: "var(--space-2)",
  },
  docItemActive: {
    borderColor: "var(--color-accent)",
    background: "var(--color-accent-soft)",
  },
  docItemInfo: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
    minWidth: 0,
    flex: 1,
  },
  docItemName: {
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-text-primary)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  docItemMeta: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
  },
  docItemActions: {
    display: "flex",
    gap: "var(--space-1)",
    flexShrink: 0,
  },
  docItemOpen: {
    padding: "var(--space-1) var(--space-3)",
    background: "var(--color-accent)",
    color: "white",
    border: "none",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-medium)",
    cursor: "pointer",
  },
  docItemDelete: {
    width: "24px",
    height: "24px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "none",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    color: "var(--color-text-tertiary)",
    cursor: "pointer",
    fontSize: "var(--text-base)",
    padding: 0,
    lineHeight: 1,
  },

  // ── Viewer panel ─────────────────────────────────────────────────────
  docViewerPanel: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-3)",
    minHeight: "400px",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-xl)",
    padding: "var(--space-4)",
    overflow: "hidden",
    minWidth: 0,
  },
  viewerToolbar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "var(--space-2)",
    flexWrap: "wrap",
  },
  viewerToolbarRight: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-2)",
  },
  pageNavLabel: {
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-text-primary)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  pageNavBtn: {
    padding: "var(--space-1) var(--space-3)",
    background: "var(--color-bg-alt)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-xs)",
    color: "var(--color-text-secondary)",
    cursor: "pointer",
    whiteSpace: "nowrap",
  },
  viewerScroll: {
    flex: 1,
    overflowY: "auto",
    maxHeight: "calc(100vh - 220px)",
    paddingRight: "var(--space-1)",
  },

  // ── Side panel ──────────────────────────────────────────────────────
  docSidePanel: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-4)",
    minWidth: 0,
  },
  sideSection: {
    padding: "var(--space-4)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-lg)",
  },
  sideTitle: {
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-primary)",
    margin: "0 0 var(--space-3) 0",
  },
  searchRow: {
    display: "flex",
    gap: "var(--space-2)",
  },
  searchInput: {
    flex: 1,
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-primary)",
    minWidth: 0,
  },
  searchClear: {
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-bg-alt)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
    cursor: "pointer",
  },
  searchNoResults: {
    padding: "var(--space-3)",
    background: "var(--color-bg-alt)",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-tertiary)",
    textAlign: "center",
    marginTop: "var(--space-2)",
  },
  searchResultsInfo: {
    marginTop: "var(--space-2)",
    marginBottom: "var(--space-2)",
  },
  searchResultsCount: {
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-accent)",
  },
  searchResults: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
    maxHeight: "260px",
    overflowY: "auto",
  },
  searchMatch: {
    display: "block",
    width: "100%",
    textAlign: "left",
    padding: "var(--space-2)",
    background: "var(--color-bg-alt)",
    border: "1px solid transparent",
    borderRadius: "var(--radius-sm)",
    cursor: "pointer",
    fontSize: "var(--text-xs)",
    lineHeight: 1.4,
  },
  searchMatchActive: {
    borderColor: "var(--color-accent)",
    background: "var(--color-accent-soft)",
  },
  searchMatchPage: {
    fontWeight: "var(--font-semibold)",
    color: "var(--color-accent)",
    display: "block",
    marginBottom: "2px",
  },
  searchMatchText: {
    color: "var(--color-text-secondary)",
  },
  selectedBox: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
  },
  selectedTextQuoted: {
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-bg-alt)",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-primary)",
    fontStyle: "italic",
    maxHeight: "120px",
    overflowY: "auto",
  },
  explainSelectedBtn: {
    padding: "var(--space-2) var(--space-4)",
    background: "var(--color-accent)",
    color: "white",
    border: "none",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-medium)",
    cursor: "pointer",
    alignSelf: "flex-start",
  },
  explainSelectedBtnDisabled: {
    opacity: 0.6,
    cursor: "wait",
  },
  sideHint: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
    margin: 0,
    lineHeight: 1.5,
  },

  // ── Footer ──────────────────────────────────────────────────────────
  footer: {
    borderTop: "1px solid var(--color-border)",
    background: "var(--color-surface)",
    padding: "var(--space-3) var(--space-6)",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    fontSize: "var(--text-xs)",
  },
  footerBrand: {
    fontWeight: "var(--font-bold)",
    color: "#c8520b",
  },
  footerTagline: {
    color: "var(--color-text-tertiary)",
  },

  // ── User feedback (thumbs up / down on explanations) ─────────────────────
  feedbackRow: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-3)",
    marginTop: "var(--space-4)",
    padding: "var(--space-3)",
    background: "var(--color-bg-alt)",
    borderRadius: "var(--radius-md)",
  },
  feedbackLabel: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
    fontWeight: "var(--font-medium)",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  feedbackBtns: {
    display: "flex",
    gap: "var(--space-2)",
  },
  feedbackBtn: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "34px",
    height: "34px",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    background: "var(--color-surface)",
    color: "var(--color-text-secondary)",
    cursor: "pointer",
    transition: "background-color var(--duration-fast) var(--ease-default), color var(--duration-fast) var(--ease-default), border-color var(--duration-fast) var(--ease-default)",
  },
  feedbackBtnActive: {
    background: "var(--color-accent)",
    borderColor: "var(--color-accent)",
    color: "white",
  },
  feedbackConfirmed: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-2)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
  },
  feedbackConfirmedIcon: {
    fontSize: "16px",
  },
  feedbackConfirmedText: {
    color: "var(--color-text-primary)",
  },
  feedbackAggregate: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
    marginLeft: "var(--space-2)",
  },
  headerBadge: {
    fontSize: "10px",
    fontWeight: "var(--font-semibold)",
    color: "#c8520b",
    background: "rgba(200, 82, 11, 0.08)",
    border: "1px solid rgba(200, 82, 11, 0.2)",
    padding: "2px 8px",
    borderRadius: "var(--radius-full)",
    letterSpacing: "0.03em",
    textTransform: "uppercase",
    whiteSpace: "nowrap",
  },
  headerActions: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-2)",
  },
  headerDocChip: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
    padding: "4px 10px",
    background: "var(--color-bg-alt)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-full)",
    fontSize: "var(--text-xs)",
    maxWidth: "180px",
  },
  headerDocName: {
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    fontWeight: "var(--font-medium)",
    color: "var(--color-text-primary)",
  },
  headerUploadBtn: {
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    padding: "6px 14px",
    background: "var(--color-accent)",
    color: "#ffffff",
    border: "none",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-semibold)",
    cursor: "pointer",
    boxShadow: "var(--shadow-sm)",
    transition: "background var(--duration-fast) var(--ease-default)",
  },
  splitLayout: {
    flex: 1,
    maxWidth: "1600px",
    margin: "0 auto",
    width: "100%",
    padding: "var(--space-5)",
  },
  errorAlert: {
    padding: "var(--space-3) var(--space-4)",
    background: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: "var(--radius-lg)",
    boxShadow: "var(--shadow-sm)",
  },
  errorRetryBtn: {
    padding: "4px 10px",
    background: "#b91c1c",
    color: "#ffffff",
    border: "none",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-medium)",
    cursor: "pointer",
  },
  errorDismissBtn: {
    padding: "4px 10px",
    background: "transparent",
    color: "#7f1d1d",
    border: "1px solid #fca5a5",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-xs)",
    cursor: "pointer",
  },
  loadingSkeletonContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
    padding: "var(--space-6)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-xl)",
    minHeight: "360px",
  },
  skeletonStageBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: "var(--space-2)",
    padding: "4px 12px",
    background: "var(--color-accent-soft)",
    border: "1px solid #fed7aa",
    borderRadius: "var(--radius-full)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-accent)",
    width: "fit-content",
    marginBottom: "var(--space-4)",
  },
  skeletonPulseDot: {
    width: "10px",
    height: "10px",
    borderRadius: "50%",
    border: "2px solid var(--color-accent)",
    borderTopColor: "transparent",
    display: "inline-block",
  },
  emptyHeader: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-3)",
    marginBottom: "var(--space-3)",
    textAlign: "left",
    width: "100%",
  },
  emptyPreviewCard: {
    width: "100%",
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-lg)",
    padding: "var(--space-4)",
    textAlign: "left",
    margin: "var(--space-2) 0",
  },
  emptyPreviewHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: "var(--space-2)",
  },
  emptyPreviewBadge: {
    fontSize: "10px",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-accent)",
    background: "var(--color-accent-soft)",
    padding: "2px 8px",
    borderRadius: "var(--radius-full)",
  },
  emptyPreviewSource: {
    fontSize: "11px",
    color: "var(--color-text-tertiary)",
  },
  emptyPreviewText: {
    fontFamily: "var(--font-devanagari)",
    fontSize: "13px",
    lineHeight: 1.6,
    color: "var(--color-text-secondary)",
    margin: "0 0 var(--space-3) 0",
    fontStyle: "italic",
  },
  emptyPreviewAnswer: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-3)",
    marginBottom: "var(--space-2)",
  },
  emptyPreviewAnswerTag: {
    fontSize: "10px",
    fontWeight: "var(--font-bold)",
    color: "#166534",
    textTransform: "uppercase",
    display: "block",
    marginBottom: "2px",
  },
  emptyPreviewAnswerText: {
    fontFamily: "var(--font-devanagari)",
    fontSize: "13px",
    lineHeight: 1.6,
    color: "var(--color-text-primary)",
    margin: 0,
  },
  emptyPreviewFooter: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    fontSize: "11px",
    color: "var(--color-text-tertiary)",
    paddingTop: "var(--space-2)",
    borderTop: "1px solid var(--color-border)",
  },
  emptyPreviewCitation: {
    color: "var(--color-accent)",
    fontWeight: "var(--font-medium)",
  },
  emptyPreviewProvenance: {
    color: "var(--color-text-secondary)",
  },
  emptyPromptsSection: {
    width: "100%",
    marginTop: "var(--space-2)",
    textAlign: "left",
  },
  emptyPromptsLabel: {
    fontSize: "11px",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-tertiary)",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    display: "block",
    marginBottom: "var(--space-2)",
  },
  emptyPromptsList: {
    display: "flex",
    flexWrap: "wrap",
    gap: "var(--space-2)",
  },
  emptyPromptBtn: {
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    padding: "6px 12px",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-full)",
    fontSize: "var(--text-xs)",
    color: "var(--color-text-secondary)",
    cursor: "pointer",
    boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
    transition: "all var(--duration-fast) var(--ease-default)",
  },
  uploadDropZone: {
    padding: "var(--space-6)",
    background: "var(--color-surface)",
    border: "2px dashed var(--color-border)",
    borderRadius: "var(--radius-xl)",
    textAlign: "center",
    cursor: "pointer",
    transition: "all var(--duration-fast) var(--ease-default)",
  },
  uploadDropZoneActive: {
    borderColor: "var(--color-accent)",
    background: "var(--color-accent-soft)",
  },
  uploadIconCircle: {
    width: "48px",
    height: "48px",
    borderRadius: "50%",
    background: "var(--color-bg-alt)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    margin: "0 auto var(--space-3) auto",
    color: "var(--color-accent)",
  },
  uploadTitle: {
    display: "block",
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-primary)",
    marginBottom: "2px",
  },
  uploadSubtitle: {
    display: "block",
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
    marginBottom: "var(--space-3)",
  },
  uploadBrowseBtn: {
    display: "inline-block",
    padding: "6px 14px",
    background: "var(--color-accent)",
    color: "#ffffff",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-medium)",
  },
  returnToExplainBtn: {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    padding: "4px 10px",
    background: "var(--color-accent-soft)",
    border: "1px solid #fed7aa",
    borderRadius: "var(--radius-full)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-accent)",
    cursor: "pointer",
  },
};
