"use client";

import React from "react";

// ── Types ──────────────────────────────────────────────────────────────
type Props = {
  explanation: ExplainResponse;
  onCitationClick: (c: { page: number; excerpt: string }) => void;
  activeCitation: number | null;
  onClearCitation: () => void;
  docId?: string;
};

// Render a markdown-ish text block into JSX-ish HTML
function renderAnswer(answer: string): React.ReactNode {
  if (!answer) return null;

  // Split into sections by **bold** headers and paragraphs
  const parts = answer.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      const title = part.slice(2, -2);
      return (
        <h4
          key={i}
          style={{
            margin: "var(--space-4) 0 var(--space-1) 0",
            fontSize: "var(--text-base)",
            fontWeight: "var(--font-semibold)",
            color: "var(--color-text-primary)",
            paddingBottom: "var(--space-1)",
            borderBottom: "1px solid var(--color-border)",
          }}
        >
          {title}
        </h4>
      );
    }
    if (part.trim() === "") return null;
    // Handle bullet points
    const lines = part.split("\n");
    return lines
      .filter((l) => l.trim())
      .map((line, j) => {
        const isBullet = line.trim().startsWith("- ") || line.trim().startsWith("• ");
        const content = isBullet ? line.replace(/^[-•]\s*/, "") : line;
        return (
          <p
            key={j}
            style={{
              margin: "var(--space-1) 0",
              padding: isBullet ? "0 var(--space-3)",
              fontSize: "var(--text-sm)",
              lineHeight: 1.6,
              color: "var(--color-text-secondary)",
              textAlign: isBullet ? "left" : "left",
              borderLeft: isBullet ? "2px solid var(--color-accent)" : "none",
            }}
          >
            {content}
          </p>
        );
      });
  });
}

export default function ExplanationPanel({
  explanation,
  onCitationClick,
  activeCitation,
  onClearCitation,
  docId,
}: Props) {
  const { explanation: expData, citations, provenance, language_used, grounding } = explanation;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.title}>Your explanation</h2>
        <div style={styles.metaRow}>
          <span style={styles.metaBadge}>
            Language: {language_used}
          </span>
          <span style={styles.metaBadge}>
            Level: {expData.explanation_level}
          </span>
        </div>
      </div>

      {/* Answer content */}
      <div style={styles.answerBox}>
        <div style={styles.answer}>{renderAnswer(expData.answer)}</div>
      </div>

      {/* Citations */}
      {citations && citations.length > 0 && (
        <div style={styles.citationsSection}>
          <h3 style={styles.sectionTitle}>Evidence</h3>
          <div style={styles.citations}>
            {citations.map((c, i) => (
              <div
                key={i}
                style={{
                  ...styles.citationCard,
                  ...(activeCitation === c.page ? styles.citationCardActive : {}),
                }}
              >
                <button
                  style={styles.citationPageBtn}
                  onClick={() => onCitationClick(c)}
                >
                  <span style={styles.citationPageNum}>Page {c.page}</span>
                </button>
                <p style={styles.citationExcerpt}>{c.excerpt}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No citations note */}
      {citations.length === 0 && (
        <div style={styles.noCitations}>
          <p>No document evidence — this explanation is based on general knowledge.</p>
          <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-tertiary)", marginTop: "var(--space-1)" }}>
            Verify important details with official sources.
          </p>
        </div>
      )}

      {/* Grounding / verification note */}
      {(grounding?.warning || grounding?.recommendation) && (
        <div style={styles.groundingSection}>
          <h3 style={styles.sectionTitle}>
            {grounding?.contradiction_found ? "⚠️ Verification warning" : "Verification"}
          </h3>
          {grounding?.contradiction_found && (
            <div style={styles.contradictionWarning}>
              <strong>This answer contains claims that conflict with the document evidence.</strong>
              <p style={styles.contradictionDetail}>
                {grounding?.contradiction_claims?.map((c, i) => (
                  <span key={i} style={styles.contradictionClaim}>
                    • "{c}"
                  </span>
                ))}
              </p>
            </div>
          )}
          {grounding?.recommendation && (
            <p style={styles.recommendation}>{grounding.recommendation}</p>
          )}
          {grounding?.confidence_band && (
            <div style={styles.confidenceRow}>
              <span style={styles.confidenceLabel}>Confidence:</span>
              <span style={{
                ...styles.confidenceValue,
                ...(grounding.confidence_band === "HIGH" ? styles.confidenceHigh : {}),
                ...(grounding.confidence_band === "MEDIUM" ? styles.confidenceMedium : {}),
                ...(grounding.confidence_band === "LOW" ? styles.confidenceLow : {}),
              }}>
                {grounding.confidence_band}
                {grounding.confidence_score != null && ` (${grounding.confidence_score})`}
              </span>
            </div>
          )}
          {grounding?.warning && (
            <p style={styles.groundingWarningText}>⚠️ {grounding.warning}</p>
          )}
        </div>
      )}

      {/* Provenance badge */}
      <div style={{ marginTop: "var(--space-3)" }}>
        <ProvenanceBadge provenance={provenance} grounding={grounding} />
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-xl)",
    padding: "var(--space-5)",
    gap: "var(--space-4)",
    overflow: "auto",
  } as React.CSSProperties,
  header: {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: "var(--space-3)",
    flexWrap: "wrap",
  } as React.CSSProperties,
  title: {
    fontSize: "var(--text-xl)",
    fontWeight: "var(--font-bold)",
    color: "var(--color-text-primary)",
    margin: 0,
  } as React.CSSProperties,
  metaRow: {
    display: "flex",
    gap: "var(--space-2)",
    flexWrap: "wrap",
  } as React.CSSProperties,
  metaBadge: {
    padding: "2px 8px",
    background: "var(--color-bg-alt)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-xs)",
    color: "var(--color-text-secondary)",
    fontWeight: "var(--font-medium)",
  } as React.CSSProperties,
  answerBox: {
    flex: 1,
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-lg)",
    padding: "var(--space-4)",
    overflow: "auto",
  } as React.CSSProperties,
  answer: {
    fontSize: "var(--text-sm)",
    lineHeight: 1.7,
    color: "var(--color-text-primary)",
  } as React.CSSProperties,
  citationsSection: {
    borderTop: "1px solid var(--color-border)",
    paddingTop: "var(--space-4)",
  } as React.CSSProperties,
  sectionTitle: {
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-primary)",
    margin: "0 0 var(--space-3) 0",
  } as React.CSSProperties,
  citations: {
    display: "flex",
    flexWrap: "wrap",
    gap: "var(--space-2)",
  } as React.CSSProperties,
  citationCard: {
    flex: "1 1 200px",
    padding: "var(--space-3)",
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    cursor: "pointer",
    transition: "all 0.15s ease",
    maxWidth: "300px",
  } as React.CSSProperties,
  citationCardActive: {
    borderColor: "var(--color-accent)",
    background: "var(--color-accent-soft)",
  } as React.CSSProperties,
  citationPageBtn: {
    display: "block",
    padding: 0,
    background: "none",
    border: "none",
    cursor: "pointer",
    marginBottom: "var(--space-1)",
    textAlign: "left",
  } as React.CSSProperties,
  citationPageNum: {
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-bold)",
    color: "var(--color-accent)",
  } as React.CSSProperties,
  citationExcerpt: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-secondary)",
    lineHeight: 1.5,
    margin: 0,
  } as React.CSSProperties,
  noCitations: {
    padding: "var(--space-3)",
    background: "var(--color-bg-alt)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
  } as React.CSSProperties,
  groundingWarning: {
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-evidence)",
    border: "1px solid var(--color-evidence-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    color: "var(--color-info)",
  } as React.CSSProperties,
  groundingSection: {
    padding: "var(--space-3)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    marginTop: "var(--space-3)",
  } as React.CSSProperties,
  contradictionWarning: {
    padding: "var(--space-2)",
    background: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: "var(--radius-sm)",
    marginBottom: "var(--space-2)",
  } as React.CSSProperties,
  contradictionDetail: {
    margin: "var(--space-1) 0 0 0",
    fontSize: "var(--text-sm)",
    color: "#991b1b",
  } as React.CSSProperties,
  contradictionClaim: {
    display: "block",
    marginBottom: "2px",
  } as React.CSSProperties,
  recommendation: {
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
    margin: "var(--space-1) 0 0 0",
    padding: "var(--space-2)",
    background: "var(--color-bg-alt)",
    borderRadius: "var(--radius-sm)",
  } as React.CSSProperties,
  confidenceRow: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-2)",
    marginTop: "var(--space-2)",
    fontSize: "var(--text-sm)",
  } as React.CSSProperties,
  confidenceLabel: {
    color: "var(--color-text-tertiary)",
    fontWeight: "var(--font-medium)",
  } as React.CSSProperties,
  confidenceValue: {
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-primary)",
  } as React.CSSProperties,
  confidenceHigh: {
    color: "#166534",
  } as React.CSSProperties,
  confidenceMedium: {
    color: "#92400e",
  } as React.CSSProperties,
  confidenceLow: {
    color: "#dc2626",
  } as React.CSSProperties,
  groundingWarningText: {
    fontSize: "var(--text-sm)",
    color: "var(--color-info)",
    marginTop: "var(--space-2)",
  } as React.CSSProperties,
};
