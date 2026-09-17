"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import {
  explainText,
  uploadDocument,
  listDocuments,
  deleteDocument,
  getDocumentViewer,
  searchDocumentText,
} from "@/lib/hamigenz-api";
import type {
  ViewerPage,
  ExplainResponse,
  DocumentInfo,
  SearchMatch,
  Citation,
} from "@/lib/types";
import ExplanationLevelSelect from "./ExplanationLevelSelect";
import ExplanationPanel from "./ExplanationPanel";
import DocumentViewer from "./DocumentViewer";
import ProvenanceBadge from "./ProvenanceBadge";

// ── Types ──────────────────────────────────────────────────────────────
type Props = {
  docId?: string;
  pages?: ViewerPage[];
  onDocUpload?: (docId: string, filename: string) => void;
  citations?: Citation[];
};

export default function WorkspacePage() {
  // ── State ───────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<"explain" | "document">("explain");
  const [explainLevel, setExplainLevel] = useState<"original" | "simple" | "very_simple">("simple");
  const [targetLang, setTargetLang] = useState<"auto" | "nepali" | "english" | "romanized_nepali">("auto");
  const [inputText, setInputText] = useState("");
  const [question, setQuestion] = useState("");
  const [explanation, setExplanation] = useState<ExplainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [viewerPages, setViewerPages] = useState<ViewerPage[]>([]);
  const [selectedText, setSelectedText] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchMatch[]>([]);
  const [activeCitation, setActiveCitation] = useState<number | null>(null);
  const [citationsByPage, setCitationsByPage] = useState<Map<number, Citation[]>>(new Map());
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Load documents ──────────────────────────────────────────────────
  useEffect(() => {
    listDocuments().then(setDocuments).catch(() => {});
  }, []);

  // ── Active doc → load viewer ────────────────────────────────────────
  useEffect(() => {
    if (!activeDocId) {
      setViewerPages([]);
      setSearchResults([]);
      return;
    }
    getDocumentViewer(activeDocId)
      .then((v) => setViewerPages(v.pages))
      .catch(() => setViewerPages([]));
  }, [activeDocId]);

  // ── Search on active doc ────────────────────────────────────────────
  useEffect(() => {
    if (!activeDocId || !searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    searchDocumentText(activeDocId, searchQuery)
      .then((r) => setSearchResults(r.matches))
      .catch(() => setSearchResults([]));
  }, [activeDocId, searchQuery]);

  // ── Explain (direct text) ───────────────────────────────────────────
  const handleExplain = useCallback(async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    setError(null);
    setLoadingStage(1);
    const stageTimer = setInterval(() => {
      setLoadingStage((prev) => {
        if (prev >= LOADING_STAGES.length) return prev;
        return prev + 1;
      });
    }, 700);
    try {
      const docId = activeDocId || undefined;
      const res = await explainText(
        inputText.trim(),
        explainLevel,
        targetLang,
        question.trim() || undefined,
        docId
      );
      setExplanation(res);
    } catch (e) {
      setError(String(e));
      setExplanation(null);
    } finally {
      clearInterval(stageTimer);
      setLoading(false);
      setLoadingStage(0);
    }
  }, [inputText, explainLevel, targetLang, question, activeDocId]);

  // ── Upload ──────────────────────────────────────────────────────────
  const handleFile = useCallback(
    async (file: File) => {
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
        if (fileInputRef.current) fileInputRef.current.value = "";
      } catch (e) {
        setError(String(e));
      }
    },
    []
  );

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
        if (activeDocId === docId) setActiveDocId(null);
      } catch (e) {
        setError(String(e));
      }
    },
    [activeDocId]
  );

  // ── Highlight text from viewer ──────────────────────────────────────
  const handleTextHighlight = useCallback(
    (text: string) => {
      setSelectedText(text);
      setInputText(text);
      setActiveTab("explain");
    },
    []
  );

  // ── Citation click → navigate to page + highlight ──────────────────
  const handleCitationClick = useCallback(
    (citation: Citation) => {
      setActiveCitation(citation.page);
      // If we have viewer pages, find the page and try to scroll into view
      const pageEl = document.getElementById(`page-${citation.page}`);
      if (pageEl) {
        pageEl.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    },
    []
  );

  // ── Build citations-by-page map from explanation ───────────────────
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

  // ── Clear highlight ─────────────────────────────────────────────────
  const clearHighlight = useCallback(() => {
    setActiveCitation(null);
    setSelectedText("");
  }, []);

  // ── Keyboard shortcut: Ctrl+Enter → explain ────────────────────────
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleExplain();
      }
    },
    [handleExplain]
  );

  // ── Loading stage management ─────────────────────────────────────────
  const [loadingStage, setLoadingStage] = useState(0);

  const LOADING_STAGES = [
    "Reading your text...",
    "Understanding the meaning...",
    "Finding the right words...",
    "Checking supporting evidence...",
    "Preparing your explanation...",
  ];

  const loadingStageText = loadingStage > 0 && loadingStage <= LOADING_STAGES.length
    ? LOADING_STAGES[loadingStage - 1]
    : "";
  return (
    <div style={styles.wrap}>
      {/* ── Header ──────────────────────────────────────────────────── */}
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <div style={styles.brand}>
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
              <rect width="32" height="32" rx="7" fill="#c8520b" />
              <path d="M9 10h14M9 16h14M9 22h10" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <circle cx="24" cy="22" r="3.5" fill="white" fillOpacity="0.9" />
            </svg>
            <span style={styles.brandName}>hamiGenZ</span>
          </div>
          <div style={styles.tabs}>
            <button
              style={{ ...styles.tab, ...(activeTab === "explain" ? styles.tabActive : {}) }}
              onClick={() => setActiveTab("explain")}
            >
              Understand text
            </button>
            <button
              style={{ ...styles.tab, ...(activeTab === "document" ? styles.tabActive : {}) }}
              onClick={() => setActiveTab("document")}
            >
              Document
            </button>
          </div>
        </div>
        <div style={styles.headerDesc}>
          Don&apos;t understand it? Ask hamiGenZ.
        </div>
      </header>

      {/* ── Main panel ───────────────────────────────────────────────── */}
      <main style={styles.main}>
        {activeTab === "explain" && (
          <div style={styles.explainLayout}>
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
                  <span style={styles.docBadgeName}>
                    {documents.find((d) => d.doc_id === activeDocId)?.filename}
                  </span>
                  <button
                    style={styles.docBadgeClear}
                    onClick={() => setActiveDocId(null)}
                    title="Switch to direct text"
                  >
                    ×
                  </button>
                </div>
              )}

              {/* Explanation level selector */}
              <div style={styles.levelRow}>
                <span style={styles.levelLabel}>Explain as:</span>
                <ExplanationLevelSelect
                  value={explainLevel}
                  onChange={setExplainLevel}
                />
              </div>

              {/* Target language */}
              <div style={styles.langRow}>
                <span style={styles.langLabel}>Answer in:</span>
                <select
                  style={styles.select}
                  value={targetLang}
                  onChange={(e) => setTargetLang(e.target.value as any)}
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
                placeholder="Paste difficult text here...
    Example: नेपाल सरकारको पासपोर्ट विभागले यस वेबसाइटमार्फत नागरिकहरूलाई अनलाइन मार्फत
    पासपोर्ट सम्बन्धी सेवाहरूको विस्तृत जानकारी प्रदान गर्दछ..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={8}
              />

              {/* Optional question */}
              <div style={styles.questionRow}>
                <input
                  style={styles.questionInput}
                  placeholder="Optional: ask a specific question..."
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={handleKeyDown}
                />
              </div>

              {/* Action buttons */}
              <div style={styles.actions}>
                <button
                  style={{
                    ...styles.explainBtn,
                    ...(loading ? styles.explainBtnLoading : {}),
                  }}
                  disabled={loading || !inputText.trim()}
                  onClick={handleExplain}
                >
                  {loading ? (
                    <span style={styles.spinner} />
                  ) : (
                    "Understand"
                  )}
                </button>
                <button
                  style={styles.clearBtn}
                  onClick={() => {
                    setInputText("");
                    setQuestion("");
                    setExplanation(null);
                    setError(null);
                  }}
                >
                  Clear
                </button>
              </div>

              {loading && (
                <p style={styles.loadingHint}>
                  {loadingStageText}
                </p>
              )}

              {error && <div style={styles.error}>{error}</div>}

              {/* Keyboard hint */}
              <p style={styles.hint}>
                Ctrl+Enter to explain · Select text in Document tab to explain
              </p>
            </div>

            {/* Right: explanation output */}
            <div style={styles.outputPanel}>
              {!explanation ? (
                <div style={styles.emptyState}>
                  <div style={styles.emptyIcon}>
                    <svg width="48" height="48" viewBox="0 0 32 32" fill="none">
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
                    Paste difficult text and click &quot;Understand&quot; to see a simple explanation.
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
                <ExplanationPanel
                  explanation={explanation}
                  onCitationClick={handleCitationClick}
                  activeCitation={activeCitation}
                  onClearCitation={clearHighlight}
                  docId={activeDocId || undefined}
                />
              )}
            </div>
          </div>
        )}

        {activeTab === "document" && (
          <div style={styles.docLayout}>
            {/* Left: document list + upload */}
            <div style={styles.docListPanel}>
              <div style={styles.panelHeader}>
                <h2 style={styles.panelTitle}>Your Documents</h2>
              </div>

              {/* Upload */}
              <div style={styles.uploadArea}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
                  style={{ display: "none" }}
                  onChange={handleFileSelect}
                  id="doc-upload"
                />
                <label
                  style={styles.uploadLabel}
                  htmlFor="doc-upload"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
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
              </div>

              {/* Document list */}
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
                          onClick={() => setActiveDocId(doc.doc_id)}
                        >
                          {activeDocId === doc.doc_id ? "Viewing" : "Open"}
                        </button>
                        <button
                          style={styles.docItemDelete}
                          onClick={() => handleDeleteDoc(doc.doc_id)}
                        >
                          ×
                        </button>
                      </div>
                    </div>
                  ))}
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
              ) : (
                <div style={styles.viewerInner}>
                  {/* Page navigation */}
                  <div style={styles.pageNav}>
                    <span style={styles.pageNavLabel}>
                      Page {activeCitation || 1} of {viewerPages.length}
                    </span>
                    <div style={styles.pageNavButtons}>
                      <button
                        style={styles.pageNavBtn}
                        disabled={!activeCitation}
                        onClick={() => setActiveCitation(null)}
                      >
                        Clear highlight
                      </button>
                    </div>
                  </div>

                  {/* Page selector tabs */}
                  <div style={styles.pageTabs}>
                    {viewerPages.map((page) => (
                      <button
                        key={page.page_num}
                        style={{
                          ...styles.pageTab,
                          ...(activeCitation === page.page_num ? styles.pageTabActive : {}),
                        }}
                        onClick={() => setActiveCitation(page.page_num)}
                      >
                        Pg {page.page_num}
                      </button>
                    ))}
                  </div>

                  {/* Page content */}
                  {viewerPages.map((page) => (
                    <DocumentViewer
                      key={page.page_num}
                      docId={activeDocId!}
                      pages={[page]}
                      onTextHighlight={handleTextHighlight}
                      activeCitation={activeCitation}
                      onCitationClick={handleCitationClick}
                      citationsByPage={citationsByPage}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Right: search + selected text explain */}
            <div style={styles.docSidePanel}>
              {/* Search */}
              <div style={styles.sideSection}>
                <h3 style={styles.sideTitle}>Search document</h3>
                <div style={styles.searchRow}>
                  <input
                    style={styles.searchInput}
                    placeholder="Search text..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  {searchResults.length > 0 && (
                    <button
                      style={styles.searchClear}
                      onClick={() => setSearchQuery("")}
                    >
                      Clear
                    </button>
                  )}
                </div>
                {searchResults.length > 0 && (
                  <div style={styles.searchResults}>
                    {searchResults.map((m, i) => (
                      <div
                        key={i}
                        style={styles.searchMatch}
                        onClick={() => {
                          setActiveCitation(m.page);
                          setSearchQuery("");
                        }}
                      >
                        <span style={styles.searchMatchPage}>Page {m.page}</span>
                        <span style={styles.searchMatchText}>
                          {m.text.slice(0, 120)}...
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Selected text explain */}
              <div style={styles.sideSection}>
                <h3 style={styles.sideTitle}>Explain selected text</h3>
                {selectedText ? (
                  <div style={styles.selectedBox}>
                    <div style={styles.selectedText}>
                      <em>"{selectedText}"</em>
                    </div>
                    <button
                      style={styles.explainSelectedBtn}
                      onClick={() => {
                        setInputText(selectedText);
                        setActiveTab("explain");
                        handleExplain();
                      }}
                    >
                      Explain this
                    </button>
                  </div>
                ) : (
                  <p style={styles.sideHint}>
                    Highlight text in the document viewer to explain it.
                  </p>
                )}
              </div>

              {/* Provenance note */}
              {explanation && (
                <div style={styles.sideSection}>
                  <ProvenanceBadge
                    provenance={explanation.provenance}
                    grounding={explanation.grounding}
                  />
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer style={styles.footer}>
        <span style={styles.footerBrand}>hamiGenZ</span>
        <span style={styles.footerTagline}>
          Don&apos;t understand it? Ask hamiGenZ.
        </span>
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
  } as React.CSSProperties,
  header: {
    borderBottom: "1px solid var(--color-border)",
    background: "var(--color-surface)",
  } as React.CSSProperties,
  headerInner: {
    maxWidth: "1200px",
    margin: "0 auto",
    padding: "var(--space-4) var(--space-6)",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "var(--space-4)",
  } as React.CSSProperties,
  brand: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-2)",
  } as React.CSSProperties,
  brandName: {
    fontWeight: "var(--font-bold)",
    fontSize: "var(--text-lg)",
    color: "#c8520b",
    letterSpacing: "-0.02em",
  } as React.CSSProperties,
  tabs: {
    display: "flex",
    gap: "var(--space-1)",
    background: "var(--color-bg-alt)",
    borderRadius: "var(--radius-md)",
    padding: "2px",
  } as React.CSSProperties,
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
  } as React.CSSProperties,
  tabActive: {
    background: "var(--color-accent)",
    color: "white",
  } as React.CSSProperties,
  headerDesc: {
    fontSize: "var(--text-sm)",
    color: "var(--color-text-tertiary)",
    textAlign: "right",
  } as React.CSSProperties,
  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
  } as React.CSSProperties,

  // ── Explain layout ──────────────────────────────────────────────────
  explainLayout: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "var(--space-6)",
    flex: 1,
    maxWidth: "1200px",
    margin: "0 auto",
    width: "100%",
    padding: "var(--space-6)",
  } as React.CSSProperties,
  inputPanel: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-4)",
  } as React.CSSProperties,
  outputPanel: {
    display: "flex",
    flexDirection: "column",
    minHeight: "400px",
  } as React.CSSProperties,
  panelHeader: {
    marginBottom: "var(--space-2)",
  } as React.CSSProperties,
  panelTitle: {
    fontSize: "var(--text-xl)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-primary)",
    margin: 0,
  } as React.CSSProperties,
  panelSubtitle: {
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
    margin: "var(--space-1) 0 0 0",
  } as React.CSSProperties,

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
  } as React.CSSProperties,
  docBadgeLabel: {
    fontWeight: "var(--font-medium)",
  } as React.CSSProperties,
  docBadgeName: {
    flex: 1,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  } as React.CSSProperties,
  docBadgeClear: {
    background: "none",
    border: "none",
    color: "var(--color-accent)",
    cursor: "pointer",
    fontSize: "var(--text-lg)",
    padding: "0 2px",
    lineHeight: 1,
  } as React.CSSProperties,

  // ── Level / language rows ───────────────────────────────────────────
  levelRow: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-3)",
  } as React.CSSProperties,
  levelLabel: {
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-text-secondary)",
    whiteSpace: "nowrap",
  } as React.CSSProperties,
  langRow: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-3)",
  } as React.CSSProperties,
  langLabel: {
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-text-secondary)",
    whiteSpace: "nowrap",
  } as React.CSSProperties,
  select: {
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-primary)",
    cursor: "pointer",
  } as React.CSSProperties,

  // ── Textarea ────────────────────────────────────────────────────────
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
    boxSizing: "border-box",
  } as React.CSSProperties,
  questionRow: {
    display: "flex",
    gap: "var(--space-2)",
    alignItems: "center",
  } as React.CSSProperties,
  questionInput: {
    flex: 1,
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-bg-alt)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-primary)",
  } as React.CSSProperties,

  // ── Actions ─────────────────────────────────────────────────────────
  actions: {
    display: "flex",
    gap: "var(--space-2)",
    marginTop: "var(--space-2)",
  } as React.CSSProperties,
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
  } as React.CSSProperties,
  explainBtnDisabled: {
    opacity: 0.6,
    cursor: "wait",
  } as React.CSSProperties,
  clearBtn: {
    padding: "var(--space-3) var(--space-4)",
    background: "var(--color-surface)",
    color: "var(--color-text-secondary)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-lg)",
    fontSize: "var(--text-sm)",
    cursor: "pointer",
  } as React.CSSProperties,
  spinner: {
    width: "16px",
    height: "16px",
    border: "2px solid rgba(255,255,255,0.3)",
    borderTopColor: "white",
    borderRadius: "50%",
    animation: "spin 0.6s linear infinite",
  } as React.CSSProperties,
  error: {
    padding: "var(--space-3)",
    background: "var(--color-evidence)",
    border: "1px solid var(--color-evidence-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    color: "var(--color-info)",
  } as React.CSSProperties,
  hint: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
    textAlign: "center",
    margin: 0,
  } as React.CSSProperties,

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
  } as React.CSSProperties,
  emptyIcon: {
    marginBottom: "var(--space-2)",
  } as React.CSSProperties,
  emptyTitle: {
    fontSize: "var(--text-lg)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-primary)",
    margin: 0,
  } as React.CSSProperties,
  emptySubtitle: {
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
    margin: 0,
    maxWidth: "300px",
  } as React.CSSProperties,
  emptyLevels: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
    width: "100%",
    maxWidth: "320px",
    marginTop: "var(--space-4)",
  } as React.CSSProperties,
  emptyLevel: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-3)",
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-bg-alt)",
    borderRadius: "var(--radius-md)",
  } as React.CSSProperties,
  emptyLevelBadge: {
    padding: "2px 8px",
    background: "var(--color-accent)",
    color: "white",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-semibold)",
    whiteSpace: "nowrap",
  } as React.CSSProperties,
  emptyLevelDesc: {
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
    flex: 1,
  } as React.CSSProperties,

  // ── Document layout ──────────────────────────────────────────────────
  docLayout: {
    display: "grid",
    gridTemplateColumns: "280px 1fr 280px",
    gap: "var(--space-6)",
    flex: 1,
    maxWidth: "1400px",
    margin: "0 auto",
    width: "100%",
    padding: "var(--space-6)",
    minHeight: "500px",
  } as React.CSSProperties,
  docListPanel: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-4)",
  } as React.CSSProperties,
  uploadArea: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
  } as React.CSSProperties,
  uploadLabel: {
    display: "flex",
    alignItems: "center",
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
  } as React.CSSProperties,
  noDocs: {
    padding: "var(--space-6)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-lg)",
    textAlign: "center",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
  } as React.CSSProperties,
  docList: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
    overflowY: "auto",
    maxHeight: "500px",
  } as React.CSSProperties,
  docItem: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "var(--space-3)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    gap: "var(--space-2)",
  } as React.CSSProperties,
  docItemActive: {
    borderColor: "var(--color-accent)",
    background: "var(--color-accent-soft)",
  } as React.CSSProperties,
  docItemInfo: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
    minWidth: 0,
  } as React.CSSProperties,
  docItemName: {
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-text-primary)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  } as React.CSSProperties,
  docItemMeta: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
    // doc.page_count is from the backend; chunks info not surfaced in list yet
    content: "attr(data-pages)",
  } as React.CSSProperties,
  docItemActions: {
    display: "flex",
    gap: "var(--space-1)",
    flexShrink: 0,
  } as React.CSSProperties,
  docItemOpen: {
    padding: "var(--space-1) var(--space-3)",
    background: "var(--color-accent)",
    color: "white",
    border: "none",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-medium)",
    cursor: "pointer",
  } as React.CSSProperties,
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
  } as React.CSSProperties,

  // ── Document viewer panel ────────────────────────────────────────────
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
  } as React.CSSProperties,
  viewerInner: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-3)",
    flex: 1,
    overflow: "auto",
  } as React.CSSProperties,
  pageNav: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  } as React.CSSProperties,
  pageNavLabel: {
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-text-primary)",
  } as React.CSSProperties,
  pageNavButtons: {
    display: "flex",
    gap: "var(--space-2)",
  } as React.CSSProperties,
  pageNavBtn: {
    padding: "var(--space-1) var(--space-3)",
    background: "var(--color-bg-alt)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-xs)",
    color: "var(--color-text-secondary)",
    cursor: "pointer",
  } as React.CSSProperties,
  pageTabs: {
    display: "flex",
    gap: "var(--space-1)",
    flexWrap: "wrap",
  } as React.CSSProperties,
  pageTab: {
    padding: "var(--space-1) var(--space-3)",
    background: "var(--color-bg-alt)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-text-secondary)",
    cursor: "pointer",
  } as React.CSSProperties,
  pageTabActive: {
    background: "var(--color-accent)",
    color: "white",
    borderColor: "var(--color-accent)",
  } as React.CSSProperties,
  pageContent: {
    padding: "var(--space-4)",
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-lg)",
  } as React.CSSProperties,
  pageContentActive: {
    borderColor: "var(--color-accent)",
    background: "var(--color-accent-soft)",
  } as React.CSSProperties,
  pageHeader: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-3)",
    marginBottom: "var(--space-3)",
    paddingBottom: "var(--space-2)",
    borderBottom: "1px solid var(--color-border)",
    flexWrap: "wrap",
  } as React.CSSProperties,
  pageLabel: {
    fontSize: "var(--text-base)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-primary)",
  } as React.CSSProperties,
  pageWords: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
  } as React.CSSProperties,
  pageHasImage: {
    fontSize: "var(--text-xs)",
    color: "var(--color-info)",
    background: "var(--color-evidence)",
    padding: "2px 6px",
    borderRadius: "var(--radius-sm)",
  } as React.CSSProperties,
  searchInfo: {
    fontSize: "var(--text-sm)",
    color: "var(--color-warning)",
    background: "var(--color-highlight)",
    padding: "var(--space-1) var(--space-2)",
    borderRadius: "var(--radius-sm)",
    marginBottom: "var(--space-2)",
  } as React.CSSProperties,
  pageText: {
    fontFamily: "var(--font-sans)",
    fontSize: "var(--text-sm)",
    lineHeight: 1.7,
    color: "var(--color-text-primary)",
    whiteSpace: "pre-wrap",
    maxHeight: "400px",
    overflowY: "auto",
  } as React.CSSProperties,
  pageTextHighlighted: {
    backgroundColor: "var(--color-highlight)",
    borderRadius: "var(--radius-md)",
  } as React.CSSProperties,
  pagePara: {
    margin: "var(--space-2) 0",
  } as React.CSSProperties,
  highlight: {
    padding: "2px 0",
    borderRadius: "2px",
    cursor: "pointer",
  } as React.CSSProperties,
  searchGap: {
    height: "var(--space-2)",
  } as React.CSSProperties,

  // ── Doc side panel ──────────────────────────────────────────────────
  docSidePanel: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-4)",
  } as React.CSSProperties,
  sideSection: {
    padding: "var(--space-4)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-lg)",
  } as React.CSSProperties,
  sideTitle: {
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-primary)",
    margin: "0 0 var(--space-3) 0",
  } as React.CSSProperties,
  searchRow: {
    display: "flex",
    gap: "var(--space-2)",
  } as React.CSSProperties,
  searchInput: {
    flex: 1,
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-primary)",
  } as React.CSSProperties,
  searchClear: {
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-bg-alt)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
    cursor: "pointer",
  } as React.CSSProperties,
  searchResults: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
    maxHeight: "200px",
    overflowY: "auto",
  } as React.CSSProperties,
  searchMatch: {
    padding: "var(--space-2)",
    background: "var(--color-bg-alt)",
    borderRadius: "var(--radius-sm)",
    cursor: "pointer",
    fontSize: "var(--text-xs)",
    lineHeight: 1.4,
  } as React.CSSProperties,
  searchMatchPage: {
    fontWeight: "var(--font-semibold)",
    color: "var(--color-accent)",
    display: "block",
    marginBottom: "2px",
  } as React.CSSProperties,
  searchMatchText: {
    color: "var(--color-text-secondary)",
  } as React.CSSProperties,
  loadingHint: {
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-info)",
    background: "var(--color-evidence)",
    padding: "6px 10px",
    borderRadius: "var(--radius-md)",
    textAlign: "center",
    margin: "8px 0 4px",
  } as React.CSSProperties,
  selectedBox: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
  } as React.CSSProperties,
  selectedText: {
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-bg-alt)",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-primary)",
    fontStyle: "italic",
  } as React.CSSProperties,
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
  } as React.CSSProperties,
  sideHint: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
    margin: 0,
    lineHeight: 1.5,
  } as React.CSSProperties,

  // ── Footer ──────────────────────────────────────────────────────────
  footer: {
    borderTop: "1px solid var(--color-border)",
    background: "var(--color-surface)",
    padding: "var(--space-3) var(--space-6)",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    fontSize: "var(--text-xs)",
  } as React.CSSProperties,
  footerBrand: {
    fontWeight: "var(--font-bold)",
    color: "#c8520b",
  } as React.CSSProperties,
  footerTagline: {
    color: "var(--color-text-tertiary)",
  } as React.CSSProperties,
};
