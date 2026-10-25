"use client";

import { useState } from "react";

const DOC_TABS = [
  { id: "simplified", label: "Simplified" },
  { id: "original",   label: "Original (Nepali)" },
] as const;

type TabId = (typeof DOC_TABS)[number]["id"];

const SIMPLIFIED_PASSAGES = [
  {
    id: "p1",
    cited: true,
    text: "Applicants must submit an original citizenship certificate (nagarikta) copy along with verified identity credentials.",
    citation: "Sample Notice · Page 1, Section 2",
  },
  {
    id: "p2",
    cited: true,
    text: "All applicants must confirm biometric scheduling prior to visiting the office for identity verification.",
    citation: "Sample Notice · Page 1, Section 3",
  },
  {
    id: "p3",
    cited: true,
    text: "District Administration Offices charge NPR 5,000 for standard 34-page passport issuance; department fast-track service costs NPR 12,000.",
    citation: "Sample Notice · Page 1, Fee Schedule",
  },
];

const ORIGINAL_TEXT =
  "जिल्ला प्रशासन कार्यालयहरूबाट ३४ पृष्ठको राहदानीका लागि रु ५,०००/- र विभागबाट द्रुत सेवा लिन चाहेमा रु १२,०००/- राजश्व दाखिला गर्नुपर्नेछ।";

const DEMO_QUESTION = "What fee do I pay for a passport?";

export default function AnimatedDocumentSandbox() {
  const [activeTab, setActiveTab] = useState<TabId>("simplified");
  const [pulsingId, setPulsingId] = useState<string | null>(null);

  return (
    <div
      className="hero-sandbox editorial-card"
      style={{
        width: "100%",
        maxWidth: "680px",
        margin: "0 auto",
        overflow: "hidden",
      }}
    >
      {/* ── Chrome bar ────────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-2)",
          padding: "10px 14px",
          borderBottom: "1px solid var(--color-border)",
          background: "var(--color-surface-raised)",
        }}
      >
        {["#ff5f57", "#febc2e", "#28c840"].map((c, i) => (
          <span
            key={i}
            style={{ width: 10, height: 10, borderRadius: "50%", background: c, flexShrink: 0 }}
            aria-hidden="true"
          />
        ))}
        <span
          style={{
            flex: 1,
            fontSize: "11px",
            fontFamily: "var(--font-mono)",
            color: "var(--color-text-muted)",
            textAlign: "center",
          }}
        >
          hamiGenZ Workspace · Document Analysis
        </span>
      </div>

      {/* ── Question bar ─────────────────────────────────────── */}
      <div
        style={{
          padding: "10px 14px",
          background: "var(--color-surface)",
          borderBottom: "1px solid var(--color-border)",
          display: "flex",
          alignItems: "center",
          gap: "10px",
        }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-muted)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <span
          style={{
            fontSize: "var(--text-sm)",
            color: "var(--color-text-secondary)",
            fontStyle: "italic",
          }}
        >
          {DEMO_QUESTION}
        </span>
      </div>

      {/* ── Tabs ─────────────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid var(--color-border)",
          background: "var(--color-surface)",
        }}
        role="tablist"
        aria-label="Document view"
      >
        {DOC_TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "8px 16px",
              fontSize: "var(--text-xs)",
              fontWeight: "var(--font-medium)",
              background: "transparent",
              border: "none",
              borderBottom: activeTab === tab.id ? "2px solid var(--color-accent)" : "2px solid transparent",
              color: activeTab === tab.id ? "var(--color-accent)" : "var(--color-text-muted)",
              cursor: "pointer",
              letterSpacing: "0.01em",
              transition: "color 0.18s ease",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Document Body ─────────────────────────────────────── */}
      <div
        style={{
          position: "relative",
          padding: "var(--space-4)",
          maxHeight: "320px",
          overflowY: "auto",
          background: "var(--color-bg)",
        }}
      >
        {/* OCR Scan Beam */}
        <div className="ocr-scan-beam" aria-hidden="true" />

        {activeTab === "simplified" && (
          <div className="anim-fade-in">
            {SIMPLIFIED_PASSAGES.map((p) => (
              <div
                key={p.id}
                className={`citation-preview-box${pulsingId === p.id ? " is-pulsing" : ""}`}
                onClick={() => setPulsingId((prev) => (prev === p.id ? null : p.id))}
                style={{
                  marginBottom: "var(--space-3)",
                  padding: "var(--space-3)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "6px",
                  background: "var(--color-surface)",
                  cursor: p.cited ? "pointer" : "default",
                }}
              >
                <p style={{ fontSize: "var(--text-sm)", lineHeight: "1.7", margin: 0 }}>
                  {p.text}
                </p>
                {p.cited && (
                  <div style={{ marginTop: "var(--space-2)", display: "flex", alignItems: "center", gap: "5px" }}>
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                    </svg>
                    <span style={{ fontSize: "10px", color: "var(--color-accent)", fontFamily: "var(--font-mono)", letterSpacing: "0.04em" }}>
                      {p.citation}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === "original" && (
          <div className="anim-fade-in">
            <div
              className="ocr-target-highlight"
              style={{
                padding: "var(--space-4)",
                borderRadius: "6px",
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
              }}
            >
              <p
                style={{
                  fontSize: "var(--text-sm)",
                  lineHeight: "1.8",
                  color: "var(--color-text-primary)",
                  margin: 0,
                  direction: "ltr",
                }}
              >
                {ORIGINAL_TEXT}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ── Status bar ───────────────────────────────────────── */}
      <div
        id="prov-anchor-sandbox"
        style={{
          padding: "6px 14px",
          background: "var(--color-surface-raised)",
          borderTop: "1px solid var(--color-border)",
          display: "flex",
          alignItems: "center",
          gap: "6px",
        }}
      >
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#15803d", flexShrink: 0 }} aria-hidden="true" />
        <span style={{ fontSize: "10px", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
          3 citations verified · illustrative sample notice (offline demo)
        </span>
      </div>
    </div>
  );
}
