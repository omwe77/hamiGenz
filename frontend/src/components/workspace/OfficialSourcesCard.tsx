"use client";

import React from "react";
import type { OfficialSourceInfo, FreshnessInfo } from "@/lib/types";

type Props = {
  sources: OfficialSourceInfo[];
  freshness: FreshnessInfo;
};

/**
 * "Why should I trust this?" — renders the official sources behind an
 * answer with authority badges and freshness warnings in plain language.
 */
export default function OfficialSourcesCard({ sources, freshness }: Props) {
  if (!sources || sources.length === 0) return null;

  const currentCount = sources.filter((s) => s.status === "current").length;

  return (
    <div style={styles.container}>
      <h4 style={styles.title}>
        Official source{sources.length !== 1 ? "s" : ""}
        <span style={styles.countBadge}>{sources.length}</span>
      </h4>

      {freshness.verdict === "stale" && (
        <div style={styles.staleWarning}>
          ⚠️ {freshness.notes || "Some sources may be outdated."}
          {freshness.stale_sources.length > 0 && (
            <div style={styles.staleDetail}>{freshness.stale_sources.join(" · ")}</div>
          )}
        </div>
      )}
      {freshness.verdict === "unknown" && (
        <div style={styles.staleWarning}>
          ℹ️ {freshness.notes || "Freshness could not be confirmed."}
        </div>
      )}
      {freshness.verdict === "current" && currentCount > 0 && (
        <div style={styles.currentNote}>
          ✓ Verified current as of {sources[0].fetched_date || sources[0].verified_date}
        </div>
      )}

      <ul style={styles.list}>
        {sources.map((s, i) => (
          <li key={s.source_id || i} style={styles.item}>
            <div style={styles.orgRow}>
              <span style={styles.org}>{s.organization}</span>
              {s.verified && s.status === "current" ? (
                <span style={styles.verifiedBadge} title={`Authority: ${s.authority_level}`}>
                  ✓ {s.authority_level}
                </span>
              ) : (
                <span style={styles.statusBadge} title="Check before relying on this">
                  {s.status}
                </span>
              )}
            </div>
            {s.doc_title && <div style={styles.docTitle}>{s.doc_title}</div>}
            {s.excerpt && (
              <div style={styles.excerpt}>“{s.excerpt.slice(0, 180)}
                {s.excerpt.length > 180 ? "…" : ""}”</div>
            )}
            <div style={styles.metaRow}>
              <a
                href={s.url}
                target="_blank"
                rel="noopener noreferrer nofollow"
                style={styles.link}
              >
                {s.url.replace(/^https?:\/\//, "").replace(/\/$/, "")}
              </a>
              {s.fetched_date && (
                <span style={styles.date}>content from {s.fetched_date}</span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: "var(--space-3)",
    background: "#f8fafc",
    border: "1px solid #dbe3ee",
    borderRadius: "var(--radius-md)",
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
  },
  title: {
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
    background: "#dbeafe",
    color: "#1e40af",
    borderRadius: "var(--radius-full)",
    padding: "0 6px",
    fontSize: "var(--text-xs)",
  },
  currentNote: {
    fontSize: "var(--text-xs)",
    color: "#166534",
    fontWeight: "var(--font-medium)",
  },
  staleWarning: {
    padding: "var(--space-2)",
    background: "#fef9c3",
    border: "1px solid #fde68a",
    borderRadius: "var(--radius-sm)",
    fontSize: "var(--text-xs)",
    color: "#92400e",
  },
  staleDetail: {
    marginTop: "var(--space-1)",
    fontSize: "var(--text-xs)",
    color: "#92400e",
  },
  list: {
    listStyle: "none",
    padding: 0,
    margin: 0,
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-3)",
  },
  item: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-1)",
    paddingBottom: "var(--space-2)",
    borderBottom: "1px solid var(--color-border-soft)",
  },
  orgRow: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-2)",
    flexWrap: "wrap",
  },
  org: {
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-semibold)",
    color: "var(--color-text-primary)",
  },
  verifiedBadge: {
    fontSize: "var(--text-xs)",
    color: "#166534",
    background: "#dcfce7",
    border: "1px solid #86efac",
    borderRadius: "var(--radius-sm)",
    padding: "1px 6px",
    whiteSpace: "nowrap",
  },
  statusBadge: {
    fontSize: "var(--text-xs)",
    color: "#92400e",
    background: "#fef9c3",
    border: "1px solid #fde68a",
    borderRadius: "var(--radius-sm)",
    padding: "1px 6px",
    whiteSpace: "nowrap",
  },
  docTitle: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-secondary)",
    fontFamily: "var(--font-devanagari)",
  },
  excerpt: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-secondary)",
    lineHeight: 1.5,
    fontFamily: "var(--font-devanagari)",
    paddingLeft: "var(--space-2)",
    borderLeft: "2px solid var(--color-border)",
  },
  metaRow: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-2)",
    flexWrap: "wrap",
  },
  link: {
    fontSize: "var(--text-xs)",
    wordBreak: "break-all",
  },
  date: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
  },
};
