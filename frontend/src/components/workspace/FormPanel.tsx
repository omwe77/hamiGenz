"use client";

import React from "react";
import type {
  FieldExplanation,
  FormDetectResponse,
  FormField,
} from "@/lib/types";

type Props = {
  /** Direct text mode: analyze this text as a possible form */
  text?: string;
  /** Document mode: analyze this document */
  docId?: string | null;
  targetLang: string;
};

/**
 * Form understanding panel (PR-010).
 * Detects whether the source looks like a form, lists its fields, and lets
 * the user ask "what should I put here?" for any field. Explanations carry
 * a clearly-marked SAMPLE frame and never contain the user's real data.
 */
export default function FormPanel({ text, docId, targetLang }: Props) {
  const [detect, setDetect] = React.useState<FormDetectResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [selectedField, setSelectedField] = React.useState<FormField | null>(null);
  const [explanation, setExplanation] = React.useState<FieldExplanation | null>(null);
  const [explainLoading, setExplainLoading] = React.useState(false);
  const [explainError, setExplainError] = React.useState<string | null>(null);

  const runDetect = React.useCallback(async () => {
    if (loading || (!text && !docId)) return;
    setLoading(true);
    setError(null);
    setSelectedField(null);
    setExplanation(null);
    try {
      const { detectFormFields } = await import("@/lib/hamigenz-api");
      const res = await detectFormFields(text || undefined, docId || undefined);
      setDetect(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [loading, text, docId]);

  const runExplain = React.useCallback(
    async (field: FormField) => {
      setExplainLoading(true);
      setExplainError(null);
      setExplanation(null);
      setSelectedField(field);
      try {
        const { explainFormField } = await import("@/lib/hamigenz-api");
        const res = await explainFormField(field.label, {
          docId: docId || undefined,
          context: text || undefined,
          page: field.page || undefined,
          language: targetLang,
        });
        setExplanation(res);
      } catch (e) {
        setExplainError(e instanceof Error ? e.message : String(e));
      } finally {
        setExplainLoading(false);
      }
    },
    [docId, text, targetLang]
  );

  const disabled = !text && !docId;
  const detection = detect?.detection;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>Form helper</h3>
        <button
          style={{ ...styles.button, ...(disabled || loading ? styles.buttonDisabled : {}) }}
          onClick={runDetect}
          disabled={disabled || loading}
        >
          {loading ? <span style={styles.spinner} aria-hidden="true" /> : "Check for form fields"}
        </button>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {!detect && !loading && !error && (
        <p style={styles.note}>
          Uploading a form? hamiGenZ can detect its fields and explain what
          belongs in each one — without filling it for you.
        </p>
      )}

      {detection && !detection.is_form && (
        <p style={styles.note}>
          This does not look like a form ({detection.field_count} possible
          field{detection.field_count !== 1 ? "s" : ""} found). Try the
          Understand or Actions tools instead.
        </p>
      )}

      {detection?.is_form && (
        <div style={styles.formFound}>
          <p style={styles.formFoundText}>
            Looks like a form — {detection.field_count} field
            {detection.field_count !== 1 ? "s" : ""} detected
            {detection.matched_keywords.length > 0 && (
              <> (keywords: {detection.matched_keywords.slice(0, 4).join(", ")})</>
            )}
          </p>
          <div style={styles.fieldList}>
            {(detect?.fields ?? []).map((f, i) => (
              <button
                key={i}
                style={{
                  ...styles.fieldChip,
                  ...(selectedField?.label === f.label ? styles.fieldChipActive : {}),
                }}
                onClick={() => runExplain(f)}
                disabled={explainLoading}
              >
                <span style={styles.fieldLabel}>{f.label}</span>
                <span style={styles.fieldPage}>p{f.page}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {explainLoading && (
        <p style={styles.note}>Understanding “{selectedField?.label}”…</p>
      )}

      {explainError && <div style={styles.error}>{explainError}</div>}

      {explanation && (
        <div style={styles.explanation}>
          {explanation.meta?.status === "hints_only" && explanation.meta.note && (
            <div style={styles.degraded}>{explanation.meta.note}</div>
          )}
          {explanation.meaning && (
            <div style={styles.row}>
              <span style={styles.rowLabel}>What it means</span>
              <span style={styles.rowText}>{explanation.meaning}</span>
            </div>
          )}
          {explanation.belongs && (
            <div style={styles.row}>
              <span style={styles.rowLabel}>What goes here</span>
              <span style={styles.rowText}>{explanation.belongs}</span>
            </div>
          )}
          {explanation.do_not_enter && (
            <div style={styles.row}>
              <span style={styles.rowLabel}>Common mistake</span>
              <span style={styles.rowText}>{explanation.do_not_enter}</span>
            </div>
          )}
          {explanation.sample_format && (
            <div style={styles.row}>
              <span style={styles.rowLabel}>Format</span>
              <span style={styles.rowText}>{explanation.sample_format}</span>
            </div>
          )}
          {explanation.example && (
            <div style={styles.sampleBox}>
              {explanation.sample_markers.map((m, i) => (
                <div key={i} style={styles.sampleMarker}>
                  {i === 0 ? m : m.replace("=== ", "— ")}
                </div>
              ))}
              <div style={styles.sampleText}>{explanation.example}</div>
            </div>
          )}
          {explanation.source_quote && (
            <div style={styles.evidenceBox}>
              <span style={styles.evidenceLabel}>
                From the form{explanation.page ? ` (page ${explanation.page})` : ""}:
              </span>
              <span style={styles.evidenceText}>{explanation.source_quote}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: "var(--space-4)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-lg)",
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-3)",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "var(--space-2)",
  },
  title: {
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-primary)",
    margin: 0,
  },
  button: {
    padding: "var(--space-1) var(--space-3)",
    background: "var(--color-accent)",
    color: "white",
    border: "none",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-medium)",
    cursor: "pointer",
    display: "inline-flex",
    alignItems: "center",
    gap: "var(--space-2)",
    whiteSpace: "nowrap",
  },
  buttonDisabled: {
    opacity: 0.6,
    cursor: "wait",
  },
  spinner: {
    width: "12px",
    height: "12px",
    border: "2px solid rgba(255,255,255,0.3)",
    borderTopColor: "white",
    borderRadius: "50%",
    display: "inline-block",
    animation: "ws-spin 0.6s linear infinite",
  },
  error: {
    padding: "var(--space-2) var(--space-3)",
    background: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-xs)",
    color: "#991b1b",
    wordBreak: "break-word",
  },
  degraded: {
    padding: "var(--space-2) var(--space-3)",
    background: "#fef9c3",
    border: "1px solid #fde68a",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-xs)",
    color: "#92400e",
  },
  note: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
    margin: 0,
    lineHeight: 1.5,
  },
  formFound: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
  },
  formFoundText: {
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-success)",
    margin: 0,
  },
  fieldList: {
    display: "flex",
    flexWrap: "wrap",
    gap: "var(--space-2)",
  },
  fieldChip: {
    display: "inline-flex",
    alignItems: "center",
    gap: "var(--space-1)",
    padding: "var(--space-1) var(--space-2)",
    background: "var(--color-bg-alt)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-full)",
    fontSize: "var(--text-xs)",
    color: "var(--color-text-primary)",
    cursor: "pointer",
    fontFamily: "var(--font-devanagari)",
  },
  fieldChipActive: {
    borderColor: "var(--color-accent)",
    background: "var(--color-accent-soft)",
  },
  fieldLabel: {
    maxWidth: "180px",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  fieldPage: {
    color: "var(--color-text-tertiary)",
    fontSize: "var(--text-xs)",
  },
  explanation: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
  },
  row: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
  },
  rowLabel: {
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-secondary)",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  rowText: {
    fontSize: "var(--text-sm)",
    color: "var(--color-text-primary)",
    lineHeight: 1.55,
    fontFamily: "var(--font-devanagari)",
  },
  sampleBox: {
    padding: "var(--space-3)",
    background: "var(--color-bg-alt)",
    border: "1px dashed var(--color-border)",
    borderRadius: "var(--radius-md)",
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-1)",
  },
  sampleMarker: {
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-bold)",
    color: "#92400e",
    letterSpacing: "0.03em",
  },
  sampleText: {
    fontSize: "var(--text-sm)",
    color: "var(--color-text-primary)",
    fontFamily: "var(--font-devanagari)",
  },
  evidenceBox: {
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-evidence)",
    border: "1px solid var(--color-evidence-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-xs)",
    color: "var(--color-info)",
    display: "flex",
    flexDirection: "column",
    gap: "2px",
  },
  evidenceLabel: {
    fontWeight: "var(--font-semibold)",
  },
  evidenceText: {
    fontFamily: "var(--font-devanagari)",
    color: "var(--color-text-primary)",
  },
};
