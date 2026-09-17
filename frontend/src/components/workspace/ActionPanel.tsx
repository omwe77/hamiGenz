"use client";

import React from "react";
import type { ActionsResponse } from "@/lib/types";

type Props = {
  actions: ActionsResponse | null;
  loading: boolean;
  error: string | null;
  onExtract: () => void;
  disabled?: boolean;
};

function Section({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  if (count === 0) return null;
  return (
    <div style={styles.section}>
      <h4 style={styles.sectionTitle}>
        {title}
        <span style={styles.countBadge}>{count}</span>
      </h4>
      {children}
    </div>
  );
}

export default function ActionPanel({
  actions,
  loading,
  error,
  onExtract,
  disabled,
}: Props) {
  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>What should I do?</h3>
        <button
          style={{
            ...styles.button,
            ...(disabled || loading ? styles.buttonDisabled : {}),
          }}
          onClick={onExtract}
          disabled={disabled || loading}
        >
          {loading ? <span style={styles.spinner} aria-hidden="true" /> : "Show actions"}
        </button>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {loading && (
        <p style={styles.note}>Reading the text and extracting actions…</p>
      )}

      {!actions && !loading && !error && (
        <p style={styles.note}>
          Extract a checklist of requirements, deadlines, fees, eligibility,
          next steps, and official links from the current text or document.
        </p>
      )}

      {actions && (
        <>
          {actions.meta?.status === "hints_only" && actions.meta.note && (
            <div style={styles.degraded}>{actions.meta.note}</div>
          )}

          <Section title="Requirements" count={actions.requirements.length}>
            <ul style={styles.list}>
              {actions.requirements.map((r, i) => (
                <li key={i} style={styles.checkItem}>
                  <span style={styles.checkbox} aria-hidden="true" />
                  <span style={styles.itemText}>{r}</span>
                </li>
              ))}
            </ul>
          </Section>

          <Section title="Deadlines" count={actions.deadlines.length}>
            <ul style={styles.list}>
              {actions.deadlines.map((d, i) => (
                <li key={i} style={styles.plainItem}>
                  <span style={styles.dateBadge}>{d.date || "—"}</span>
                  <span style={styles.itemText}>{d.description}</span>
                  {d.unverified && (
                    <span style={styles.unverified} title="Not confirmed in the source text">
                      unverified
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </Section>

          <Section title="Fees" count={actions.fees.length}>
            <ul style={styles.list}>
              {actions.fees.map((f, i) => (
                <li key={i} style={styles.plainItem}>
                  <span style={styles.feeBadge}>{f.amount}</span>
                  <span style={styles.itemText}>{f.description}</span>
                  {f.unverified && (
                    <span style={styles.unverified} title="Not confirmed in the source text">
                      unverified
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </Section>

          <Section title="Who does this apply to?" count={actions.eligibility.length}>
            <ul style={styles.list}>
              {actions.eligibility.map((e, i) => (
                <li key={i} style={styles.plainItem}>
                  <span style={styles.itemText}>{e}</span>
                </li>
              ))}
            </ul>
          </Section>

          <Section title="Next steps" count={actions.next_steps.length}>
            <ol style={styles.list}>
              {actions.next_steps.map((s, i) => (
                <li key={i} style={styles.plainItem}>
                  <span style={styles.stepNum}>{i + 1}.</span>
                  <span style={styles.itemText}>{s}</span>
                </li>
              ))}
            </ol>
          </Section>

          <Section title="Official links" count={actions.official_links.length}>
            <ul style={styles.list}>
              {actions.official_links.map((l, i) => (
                <li key={i} style={styles.plainItem}>
                  <a
                    href={l.url}
                    target="_blank"
                    rel="noopener noreferrer nofollow"
                    style={styles.link}
                  >
                    {l.url.replace(/^https?:\/\//, "")}
                  </a>
                  {l.classification === "verified_official" && (
                    <span
                      style={styles.verifiedBadge}
                      title={l.source_name ? `Curated source: ${l.source_name}` : "In hamiGenZ's curated official-source registry"}
                    >
                      ✓ verified official
                    </span>
                  )}
                  {l.classification === "unverified" && (
                    <span
                      style={styles.unverifiedLinkBadge}
                      title="Not in hamiGenZ's curated registry — verify carefully before relying on it"
                    >
                      unverified source
                    </span>
                  )}
                  {l.description && (
                    <span style={styles.itemText}> — {l.description}</span>
                  )}
                </li>
              ))}
            </ul>
          </Section>

          {actions.requirements.length === 0 &&
            actions.deadlines.length === 0 &&
            actions.fees.length === 0 &&
            actions.eligibility.length === 0 &&
            actions.next_steps.length === 0 &&
            actions.official_links.length === 0 && (
              <p style={styles.note}>
                No clear actions (requirements, deadlines, fees) were found in
                this text.
              </p>
            )}
        </>
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
  section: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
  },
  sectionTitle: {
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-secondary)",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    margin: 0,
    display: "flex",
    alignItems: "center",
    gap: "var(--space-2)",
  },
  countBadge: {
    background: "var(--color-bg-alt)",
    color: "var(--color-text-tertiary)",
    borderRadius: "var(--radius-full)",
    padding: "0 6px",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-medium)",
  },
  list: {
    listStyle: "none",
    padding: 0,
    margin: 0,
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
  },
  checkItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: "var(--space-2)",
    fontSize: "var(--text-sm)",
    lineHeight: 1.5,
  },
  checkbox: {
    width: "14px",
    height: "14px",
    border: "2px solid var(--color-accent)",
    borderRadius: "3px",
    flexShrink: 0,
    marginTop: "2px",
    display: "inline-block",
  },
  plainItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: "var(--space-2)",
    fontSize: "var(--text-sm)",
    lineHeight: 1.5,
    flexWrap: "wrap",
  },
  itemText: {
    color: "var(--color-text-primary)",
    flex: 1,
    minWidth: "120px",
    fontFamily: "var(--font-devanagari)",
  },
  dateBadge: {
    background: "var(--color-accent-soft)",
    color: "var(--color-accent)",
    fontWeight: "var(--font-semibold)",
    borderRadius: "var(--radius-sm)",
    padding: "1px 6px",
    fontSize: "var(--text-xs)",
    whiteSpace: "nowrap",
    fontFamily: "var(--font-mono)",
  },
  feeBadge: {
    background: "var(--color-evidence)",
    color: "var(--color-info)",
    fontWeight: "var(--font-semibold)",
    borderRadius: "var(--radius-sm)",
    padding: "1px 6px",
    fontSize: "var(--text-xs)",
    whiteSpace: "nowrap",
  },
  stepNum: {
    color: "var(--color-accent)",
    fontWeight: "var(--font-semibold)",
    flexShrink: 0,
  },
  unverified: {
    fontSize: "var(--text-xs)",
    color: "#92400e",
    background: "#fef9c3",
    borderRadius: "var(--radius-sm)",
    padding: "1px 6px",
    whiteSpace: "nowrap",
  },
  link: {
    fontSize: "var(--text-xs)",
    wordBreak: "break-all",
  },
  verifiedBadge: {
    fontSize: "var(--text-xs)",
    color: "#166534",
    background: "#dcfce7",
    border: "1px solid #86efac",
    borderRadius: "var(--radius-sm)",
    padding: "1px 6px",
    whiteSpace: "nowrap",
    fontWeight: "var(--font-semibold)",
  },
  unverifiedLinkBadge: {
    fontSize: "var(--text-xs)",
    color: "#92400e",
    background: "#fef9c3",
    border: "1px solid #fde68a",
    borderRadius: "var(--radius-sm)",
    padding: "1px 6px",
    whiteSpace: "nowrap",
  },
};
