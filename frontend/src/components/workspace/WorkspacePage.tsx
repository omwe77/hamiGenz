"use client";

import { useState, useCallback, useRef, useEffect } from "react";
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

const LOADING_STAGES = [
  "Reading your text...",
  "Understanding the meaning...",
  "Finding the right words...",
  "Checking supporting evidence...",
  "Preparing your explanation...",
];

const EXAMPLE_PROMPTS = [
  "यो सूचनामा वास्तवमा के भन्न खोजिएको हो?",
  "yo notice ko simple meaning ke ho?",
  "passport banauna k k chainxa?",
  "What do I need to submit?",
];

export default function WorkspacePage() {
  // ── Explain state ───────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<"explain" | "document">("explain");
  const [explainLevel, setExplainLevel] = useState<ExplainLevel>("simple");
  const [targetLang, setTargetLang] = useState<TargetLang>("auto");
  const [inputText, setInputText] = useState("");
  const [question, setQuestion] = useState("");
  const [explanation, setExplanation] = useState<ExplainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // ── Document state ──────────────────────────────────────────────────
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [viewerPages, setViewerPages] = useState<ViewerPage[]>([]);
  const [viewerLoading, setViewerLoading] = useState(false);
  const [selectedText, setSelectedText] = useState("");

  // ── Search state ────────────────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchMatch[]>([]);
  const [activeSearchMatchIdx, setActiveSearchMatchIdx] = useState<number | null>(null);

  // ── Citation/highlight state ────────────────────────────────────────
  const [citationsByPage, setCitationsByPage] = useState<Map<number, Citation[]>>(new Map());
  const [highlightPage, setHighlightPage] = useState<number | null>(null);

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
  const stageTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Load documents once ─────────────────────────────────────────────
  useEffect(() => {
    listDocuments().then(setDocuments).catch(() => {});
  }, []);

  // ── Active doc → load viewer ────────────────────────────────────────
  useEffect(() => {
    if (!activeDocId) {
      setViewerPages([]);
      return;
    }
    setViewerLoading(true);
    getDocumentViewer(activeDocId)
      .then((v) => setViewerPages(v.pages))
      .catch(() => setViewerPages([]))
      .finally(() => setViewerLoading(false));
  }, [activeDocId]);

  // ── Debounced search on active doc ──────────────────────────────────
  useEffect(() => {
    if (!activeDocId || !searchQuery.trim()) {
      setSearchResults([]);
      setActiveSearchMatchIdx(null);
      return;
    }
    const t = setTimeout(() => {
      searchDocumentText(activeDocId, searchQuery.trim())
        .then((r) => {
          setSearchResults(r.matches);
          setActiveSearchMatchIdx(null);
        })
        .catch(() => setSearchResults([]));
    }, 300);
    return () => clearTimeout(t);
  }, [activeDocId, searchQuery]);

  // ── Build citations-by-page map when explanation changes ───────────
  useEffect(() => {
    const map = new Map<number, Citation[]>();
    if (explanation?.citations) {
      for (const c of explanation.citations) {
        const list = map.get(c.page) || [];
        list.push(c);
        map.set(c.page, list);
      }
    }
    setCitationsByPage(map);
  }, [explanation]);

  // ── Clear stage timer on unmount ────────────────────────────────────
  useEffect(() => {
    return () => {
      if (stageTimerRef.current) clearInterval(stageTimerRef.current);
    };
  }, []);

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
      setLoadingStage(1);
      if (stageTimerRef.current) clearInterval(stageTimerRef.current);
      stageTimerRef.current = setInterval(() => {
        setLoadingStage((prev) =>
          prev >= LOADING_STAGES.length ? prev : prev + 1
        );
      }, 900);
      try {
        const res = await explainText(text, level, lang, q, docId);
        setExplanation(res);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (stageTimerRef.current) clearInterval(stageTimerRef.current);
        stageTimerRef.current = null;
        setLoading(false);
        setLoadingStage(0);
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
      setActiveTab("document");
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

  const handleDeleteDoc = useCallback(
    async (docId: string) => {
      try {
        await deleteDocument(docId);
        setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
        if (activeDocId === docId) {
          setActiveDocId(null);
          setViewerPages([]);
          setSelectedText("");
          setSearchQuery("");
          setSearchResults([]);
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
    setActiveTab("document");
    setHighlightPage(citation.page);
    setActiveSearchMatchIdx(null);
    // Wait for the document tab to render, then scroll
    setTimeout(() => {
      const pageEl = document.getElementById(`page-${citation.page}`);
      pageEl?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 80);
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
  const loadingStageText =
    loadingStage > 0 && loadingStage <= LOADING_STAGES.length
      ? LOADING_STAGES[loadingStage - 1]
      : "";

  return (
    <div style={styles.wrap}>
      {/* ── Header ──────────────────────────────────────────────────── */}
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <a href="/" style={styles.brand} aria-label="hamiGenZ home">
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <rect width="32" height="32" rx="7" fill="#c8520b" />
              <path d="M9 10h14M9 16h14M9 22h10" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <circle cx="24" cy="22" r="3.5" fill="white" fillOpacity="0.9" />
            </svg>
            <span style={styles.brandName}>hamiGenZ</span>
          </a>
          <nav style={styles.tabs} aria-label="Workspace mode">
            <button
              style={{ ...styles.tab, ...(activeTab === "explain" ? styles.tabActive : {}) }}
              onClick={() => setActiveTab("explain")}
              aria-pressed={activeTab === "explain"}
            >
              Understand text
            </button>
            <button
              style={{ ...styles.tab, ...(activeTab === "document" ? styles.tabActive : {}) }}
              onClick={() => setActiveTab("document")}
              aria-pressed={activeTab === "document"}
            >
              Document
            </button>
          </nav>
        </div>
        <div style={styles.headerDesc}>Don&apos;t understand it? Ask hamiGenZ.</div>
      </header>

      {/* ── Main panel ───────────────────────────────────────────────── */}
      <main style={styles.main}>
        {activeTab === "explain" && (
          <div className="ws-grid-2" style={styles.explainLayout}>
            {/* Left: input panel */}
            <div style={styles.inputPanel}>
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
                    onClick={() => setActiveDocId(null)}
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
                      key={ex}
                      style={styles.exampleChip}
                      onClick={() => setInputText(ex)}
                    >
                      {ex}
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
                {loading && loadingStageText && (
                  <p style={styles.loadingHint}>{loadingStageText}</p>
                )}
              </div>

              {error && <div style={styles.errorBox}>{error}</div>}

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
            <div style={styles.outputPanel}>
              {!explanation ? (
                <div style={styles.emptyState}>
                  <div style={styles.emptyIcon}>
                    <svg width="48" height="48" viewBox="0 0 32 32" fill="none" aria-hidden="true">
                      <rect width="32" height="32" rx="7" fill="#c8520b" fillOpacity="0.15" />
                      <path
                        d="M9 10h14M9 16h14M9 22h10"
                        stroke="#c8520b"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                      <circle cx="24" cy="22" r="3.5" fill="#c8520b" fillOpacity="0.3" />
                    </svg>
                  </div>
                  <h3 style={styles.emptyTitle}>Your explanation will appear here</h3>
                  <p style={styles.emptySubtitle}>
                    Paste difficult text and click &quot;Understand&quot; to see a simple
                    explanation.
                  </p>
                  <div style={styles.emptyLevels}>
                    <div style={styles.emptyLevel}>
                      <span style={styles.emptyLevelBadge}>Original</span>
                      <span style={styles.emptyLevelDesc}>
                        Preserve formal wording, explain meaning
                      </span>
                    </div>
                    <div style={styles.emptyLevel}>
                      <span style={styles.emptyLevelBadge}>Simple</span>
                      <span style={styles.emptyLevelDesc}>
                        Everyday language, exact meaning preserved
                      </span>
                    </div>
                    <div style={styles.emptyLevel}>
                      <span style={styles.emptyLevelBadge}>Very Simple</span>
                      <span style={styles.emptyLevelDesc}>
                        Short sentences, every term explained
                      </span>
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
                            aria-label="Thumbs up"
                            title="Thumbs up"
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                              <path d="M14 18c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm4-12.5c-2.3 0-4.3 1.5-5.1 3.5-.8 2-.3 4.2 1.2 5.6 3.2 2.8 8.3 2.8 11.5 0 1.5-1.4 1.9-3.6 1.2-5.6-.8-2-2.8-3.5-5.1-3.5h-.5zm-2 5.5c0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2 2 .9 2 2zm-6 0c0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2 2 .9 2 2zm8 0c0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2 2 .9 2 2z" fill="currentColor" />
                            </svg>
                          </button>
                          <button
                            style={{
                              ...styles.feedbackBtn,
                              ...(feedback.rating === -1 ? styles.feedbackBtnActive : {}),
                            }}
                            onClick={() => handleFeedback(-1)}
                            aria-label="Thumbs down"
                            title="Thumbs down"
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                              <path d="M16 18c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm-8 0c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm4-12.5c-2.3 0-4.3 1.5-5.1 3.5-.8 2-.3 4.2 1.2 5.6 3.2 2.8 8.3 2.8 11.5 0 1.5-1.4 1.9-3.6 1.2-5.6-.8-2-2.8-3.5-5.1-3.5h-.5zm-2 5.5c0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2 2 .9 2 2zm-6 0c0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2 2 .9 2 2zm8 0c0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2 2 .9 2 2z" fill="currentColor" />
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
          </div>
        )}

        {activeTab === "document" && (
          <div className="ws-grid-3" style={styles.docLayout}>
            {/* Left: document list + upload */}
            <div style={styles.docListPanel}>
              <div style={styles.panelHeader}>
                <h2 style={styles.panelTitle}>Your Documents</h2>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
                style={{ display: "none" }}
                onChange={handleFileSelect}
                id="doc-upload"
              />
              <label style={styles.uploadLabel} htmlFor="doc-upload">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path
                    d="M12 4v12m0 0l-4-4m4 4l4-4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                Upload document (PDF, image)
              </label>

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
                    <span style={styles.pageNavLabel}>
                      {viewerPages.length} page{viewerPages.length !== 1 ? "s" : ""}
                      {activeDoc ? ` · ${activeDoc.filename}` : ""}
                    </span>
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
                    onChange={(e) => setSearchQuery(e.target.value)}
                    aria-label="Search document text"
                  />
                  {searchQuery && (
                    <button style={styles.searchClear} onClick={() => setSearchQuery("")}>
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
    maxWidth: "1200px",
    margin: "0 auto",
    padding: "var(--space-4) var(--space-6)",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "var(--space-4)",
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
    transition: "all 0.15s ease",
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
    transition: "all 0.15s ease",
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
    transition: "all 0.15s ease",
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
    transition: "all 0.15s ease",
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
};
