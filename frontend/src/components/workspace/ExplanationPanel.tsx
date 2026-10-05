"use client";

import React from "react";
import type { ExplainResponse } from "@/lib/types";
import ProvenanceBadge from "./ProvenanceBadge";
import OfficialSourcesCard from "./OfficialSourcesCard";

// ── Types ──────────────────────────────────────────────────────────────
type Props = {
  explanation: ExplainResponse;
  onCitationClick: (c: { page: number; excerpt: string }) => void;
  activeCitation: number | null;
  /** @deprecated kept for call-site compat; no longer used internally */
  onClearCitation?: () => void;
  /** @deprecated kept for call-site compat; no longer used internally */
  docId?: string;
  sourceUnavailable?: boolean;
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
              padding: isBullet ? "0 var(--space-3)" : "0",
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
  sourceUnavailable,
}: Props) {
  const { explanation: expData, citations, provenance, language_used } = explanation;
  const grounding = explanation.grounding;
  // Official-source answering fields (PR-012) — present when this payload
  // came through the official pipeline.
  const officialSources = (explanation as unknown as {
    official_sources?: Parameters<typeof OfficialSourcesCard>[0]["sources"];
    freshness?: Parameters<typeof OfficialSourcesCard>[0]["freshness"];
  }).official_sources;
  const freshness = (explanation as unknown as {
    freshness?: Parameters<typeof OfficialSourcesCard>[0]["freshness"];
  }).freshness;

  return (
    <div style={styles.container}>
      {/* 1. User's Question (Context) */}
      {expData.question && (
        <div style={styles.questionBlock}>
          <span style={styles.sectionLabel}>Your Question</span>
          <h3 style={styles.questionText}>“{expData.question}”</h3>
        </div>
      )}

      {/* 2. Primary Plain-Language Answer */}
      <div style={styles.answerSection}>
        <div style={styles.answerHeader}>
          <span style={styles.sectionLabel}>Plain-Language Explanation</span>
          <div style={styles.metaRow}>
            <span style={styles.metaText}>{language_used}</span>
            <span style={styles.metaDot}>·</span>
            <span style={styles.metaText}>{expData.explanation_level}</span>
          </div>
        </div>
        <div style={styles.answerBody}>{renderAnswer(expData.answer)}</div>
      </div>

      {/* 3. Evidence / Citations */}
      {citations && citations.length > 0 && (
        <div style={styles.citationsSection}>
          <div style={styles.sectionHeader}>
            <span style={styles.sectionLabel}>Verified Source Evidence ({citations.length})</span>
            <span style={styles.citationHelpText}>Click an excerpt to inspect page proof</span>
          </div>
          <div style={styles.citations}>
            {citations.map((c, i) => (
              <button
                key={i}
                type="button"
                className="touch-target-expand"
                style={{
                  ...styles.citationCard,
                  ...(activeCitation === c.page ? styles.citationCardActive : {}),
                }}
                onClick={() => onCitationClick(c)}
                aria-pressed={activeCitation === c.page}
                aria-label={`Jump to citation excerpt on page ${c.page}`}
              >
                <div style={styles.citationHeader}>
                  <span style={styles.citationPageNum}>📄 Page {c.page}</span>
                  <span style={styles.citationInspectHint}>
                    {activeCitation === c.page ? "Highlighted" : "Inspect →"}
                  </span>
                </div>
                <p style={styles.citationExcerpt}>“{c.excerpt}”</p>
              </button>
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
      {grounding && (
        <div style={styles.groundingSection}>
          <h3 style={styles.sectionTitle}>
            {grounding.contradiction_found ? "⚠️ Verification warning" : "Verification"}
          </h3>
          {grounding.contradiction_found && (
            <div style={styles.contradictionWarning}>
              <strong>This answer contains claims that conflict with the document evidence.</strong>
              <p style={styles.contradictionDetail}>
                {grounding.contradiction_claims?.map((c, i) => (
                  <span key={i} style={styles.contradictionClaim}>
                    • &ldquo;{c}&rdquo;
                  </span>
                ))}
              </p>
            </div>
          )}
          {grounding.recommendation && (
            <p style={styles.recommendation}>{grounding.recommendation}</p>
          )}
          {grounding.confidence_band && (
            <div style={styles.confidenceRow}>
              <span style={styles.confidenceLabel}>Confidence:</span>
              <span style={{
                ...styles.confidenceValue,
                ...(grounding.confidence_band === "HIGH" ? styles.confidenceHigh : {}),
                ...(grounding.confidence_band === "MEDIUM" ? styles.confidenceMedium : {}),
                ...(grounding.confidence_band === "LOW" ? styles.confidenceLow : {}),
                ...(grounding.confidence_band === "UNKNOWN" ? styles.confidenceUnknown : {}),
              }}>
                {grounding.confidence_band === "UNKNOWN" && !grounding.confidence_score
                  ? "Not verified"
                  : `${grounding.confidence_band}${grounding.confidence_score != null ? ` (${grounding.confidence_score})` : ""}`}
              </span>
            </div>
          )}
          {grounding.warning && (
            <p style={styles.groundingWarningText}>⚠️ {grounding.warning}</p>
          )}
          {grounding.overall_confidence === "LOW" && !grounding.contradiction_found && (
            <p style={styles.lowEvidenceNote}>
              This answer could not be fully verified from the available source.
              Important details may be missing or imprecise — check the original source.
            </p>
          )}
        </div>
      )}

      {/* Official sources — why should I trust this? (PR-012) */}
      {officialSources && officialSources.length > 0 && freshness && (
        <OfficialSourcesCard sources={officialSources} freshness={freshness} />
      )}

      {/* Provenance badge */}
      <div style={{ marginTop: "var(--space-3)" }}>
        <ProvenanceBadge provenance={provenance} grounding={grounding} sourceUnavailable={sourceUnavailable} />
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
    padding: "var(--space-6)",
    gap: "var(--space-5)",
    overflow: "auto",
  } as React.CSSProperties,
  questionBlock: {
    padding: "var(--space-3) var(--space-4)",
    background: "var(--color-bg-alt)",
    borderLeft: "3px solid var(--color-accent)",
    borderRadius: "0 var(--radius-md) var(--radius-md) 0",
  } as React.CSSProperties,
  sectionLabel: {
    display: "block",
    fontSize: "11px",
    fontWeight: "var(--font-semibold)",
    letterSpacing: "0.06em",
    textTransform: "uppercase",
    color: "var(--color-text-tertiary)",
    marginBottom: "4px",
  } as React.CSSProperties,
  questionText: {
    fontFamily: "var(--font-devanagari)",
    fontSize: "var(--text-base)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-primary)",
    margin: 0,
    lineHeight: 1.5,
  } as React.CSSProperties,
  answerSection: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
  } as React.CSSProperties,
  answerHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    paddingBottom: "var(--space-2)",
    borderBottom: "1px solid var(--color-border)",
  } as React.CSSProperties,
  metaRow: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
  } as React.CSSProperties,
  metaText: {
    fontSize: "11px",
    color: "var(--color-text-tertiary)",
    fontWeight: "var(--font-medium)",
    textTransform: "capitalize",
  } as React.CSSProperties,
  metaDot: {
    fontSize: "11px",
    color: "var(--color-text-tertiary)",
  } as React.CSSProperties,
  answerBody: {
    fontFamily: "var(--font-devanagari)",
    fontSize: "1rem", /* 16px */
    lineHeight: 1.85,
    color: "var(--color-text-primary)",
    paddingTop: "var(--space-2)",
  } as React.CSSProperties,
  citationsSection: {
    borderTop: "1px solid var(--color-border)",
    paddingTop: "var(--space-4)",
  } as React.CSSProperties,
  sectionHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: "var(--space-3)",
    flexWrap: "wrap",
    gap: "var(--space-2)",
  } as React.CSSProperties,
  citationHelpText: {
    fontSize: "11px",
    color: "var(--color-text-tertiary)",
  } as React.CSSProperties,
  citationInspectHint: {
    fontSize: "11px",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-accent)",
  } as React.CSSProperties,
  citations: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
    gap: "var(--space-3)",
  } as React.CSSProperties,
  citationCard: {
    display: "flex",
    flexDirection: "column",
    padding: "var(--space-3) var(--space-4)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-lg)",
    cursor: "pointer",
    textAlign: "left",
    font: "inherit",
    appearance: "none",
    boxShadow: "var(--shadow-sm)",
    transition: "all var(--duration-fast) var(--ease-default)",
  } as React.CSSProperties,
  citationCardActive: {
    borderColor: "var(--color-citation-border)",
    background: "var(--color-citation)",
    boxShadow: "0 0 0 2px var(--color-citation-border), var(--shadow-sm)",
    transform: "translateY(-1px)",
  } as React.CSSProperties,
  citationHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    width: "100%",
    marginBottom: "var(--space-2)",
  } as React.CSSProperties,
  citationBadge: {
    fontSize: "10px",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-citation-text)",
    background: "rgba(245, 158, 11, 0.15)",
    padding: "2px 8px",
    borderRadius: "var(--radius-full)",
    border: "1px solid var(--color-citation-border)",
    letterSpacing: "0.03em",
  } as React.CSSProperties,
  citationPageNum: {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-bold)",
    color: "var(--color-accent)",
  } as React.CSSProperties,
  citationExcerpt: {
    fontFamily: "var(--font-devanagari)",
    fontSize: "12px",
    color: "var(--color-text-secondary)",
    lineHeight: 1.6,
    margin: 0,
    display: "-webkit-box",
    WebkitLineClamp: 3,
    WebkitBoxOrient: "vertical",
    overflow: "hidden",
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
  confidenceUnknown: {
    color: "#8a8a8a",
    fontStyle: "italic",
  } as React.CSSProperties,
  groundingWarningText: {
    fontSize: "var(--text-sm)",
    color: "var(--color-info)",
    marginTop: "var(--space-2)",
  } as React.CSSProperties,
};
