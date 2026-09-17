"use client";

import React, { useState } from "react";
import { ViewerPage, Citation } from "@/lib/types";
import CitationChip from "./CitationChip";

type Props = {
  docId: string;
  pages: ViewerPage[];
  onTextHighlight: (text: string) => void;
  activeCitation: number | null;
  onCitationClick: (c: Citation) => void;
  citationsByPage: Map<number, Citation[]>;
};

export default function DocumentViewer({ docId, pages, onTextHighlight, activeCitation, onCitationClick, citationsByPage }: Props) {
  const [selectedPage, setSelectedPage] = useState<number | null>(
    activeCitation || (pages.length > 0 ? pages[0].page_num : null)
  );

  const activeCitations = citationsByPage.get(activeCitation || 0) || [];

  if (pages.length === 0) {
    return (
      <div style={styles.empty}>
        <p>No pages found for this document.</p>
      </div>
    );
  }

  const page = pages.find((p) => p.page_num === selectedPage) || pages[0];

  return (
    <div style={styles.viewer}>
      {/* Page navigation */}
      <div style={styles.pageNav}>
        <button
          style={styles.pageBtn}
          disabled={selectedPage === 1}
          onClick={() => setSelectedPage((p) => (p !== null ? Math.max(1, p - 1) : 1))}
        >
          ← Prev
        </button>
        <span style={styles.pageIndicator}>
          Page {selectedPage} of {pages.length}
        </span>
        <button
          style={styles.pageBtn}
          disabled={selectedPage === pages.length}
          onClick={() =>
            setSelectedPage((p) =>
              p !== null ? Math.min(pages.length, p + 1) : pages.length
            )
          }
        >
          Next →
        </button>
      </div>

      {/* Page tabs (quick jump) */}
      <div style={styles.pageTabs}>
        {pages.map((p) => (
          <button
            key={p.page_num}
            style={{
              ...styles.pageTab,
              ...(selectedPage === p.page_num ? styles.pageTabActive : {}),
            }}
            onClick={() => setSelectedPage(p.page_num)}
          >
            Pg {p.page_num}
          </button>
        ))}
      </div>

      {/* Page content */}
      <div
        id={`page-${page.page_num}`}
        style={{
          ...styles.pageContent,
          ...(selectedPage === activeCitation ? styles.pageContentActive : {}),
        }}
      >
        <div style={styles.pageHeader}>
          <span style={styles.pageLabel}>Page {page.page_num}</span>
          <span style={styles.pageWords}>{page.word_count} words</span>
          {page.has_image && (
            <span style={styles.pageHasImage}>has scanned image</span>
          )}
        </div>

        {/* Extracted text with clickable highlights and active citation highlighting */}
        <div
          style={{
            ...styles.pageText,
            ...(activeCitations.length > 0 ? styles.pageTextHighlighted : {}),
          }}
          onMouseUp={(e) => {
            const sel = window.getSelection();
            if (sel && sel.toString().trim().length > 0) {
              onTextHighlight(sel.toString().trim());
            }
          }}
        >
          {page.text.split("\n").map((para, i) => {
            // If there are active citations, check whether this paragraph
            // contains any of their excerpts and wrap those excerpts in a highlight span.
            if (activeCitations.length > 0 && para.trim()) {
              let processed = para;
              const highlights: { start: number; end: number }[] = [];
              for (const c of activeCitations) {
                const idx = processed.toLowerCase().indexOf(c.excerpt.toLowerCase());
                if (idx !== -1) {
                  highlights.push({ start: idx, end: idx + c.excerpt.length });
                }
              }
              if (highlights.length > 0) {
                // Sort and build highlighted string (simple approach: wrap first match)
                highlights.sort((a, b) => a.start - b.start);
                const h = highlights[0];
                const before = processed.slice(0, h.start);
                const match = processed.slice(h.start, h.end);
                const after = processed.slice(h.end);
                return (
                  <p key={i} style={styles.pagePara}>
                    {before}
                    <span style={styles.highlight}>{match}</span>
                    {after}
                  </p>
                );
              }
            }
            return <p key={i} style={styles.pagePara}>{para}</p>;
          })}
        </div>

        {/* Citation chips for this page */}
        {citationsByPage.has(page.page_num) && citationsByPage.get(page.page_num)!.length > 0 && (
          <div style={styles.citationRow}>
            {citationsByPage.get(page.page_num)!.map((c, i) => (
              <CitationChip
                key={i}
                citation={c}
                active={activeCitation === c.page}
                onClick={() => onCitationClick(c)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  empty: {
    padding: "var(--space-8)",
    textAlign: "center",
    color: "var(--color-text-tertiary)",
    fontSize: "var(--text-sm)",
  } as React.CSSProperties,
  viewer: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-3)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-xl)",
    padding: "var(--space-4)",
    minHeight: "300px",
  } as React.CSSProperties,
  pageNav: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "var(--space-3)",
  } as React.CSSProperties,
  pageBtn: {
    padding: "var(--space-1) var(--space-4)",
    background: "var(--color-bg-alt)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    color: "var(--color-text-secondary)",
    cursor: "pointer",
  } as React.CSSProperties,
  pageIndicator: {
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-text-primary)",
  } as React.CSSProperties,
  pageTabs: {
    display: "flex",
    gap: "var(--space-1)",
    flexWrap: "wrap",
    justifyContent: "center",
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
  pageText: {
    fontFamily: "var(--font-devanagari)",
    fontSize: "var(--text-sm)",
    lineHeight: 1.7,
    color: "var(--color-text-primary)",
    whiteSpace: "pre-wrap",
    maxHeight: "400px",
    overflowY: "auto",
  } as React.CSSProperties,
  pageTextHighlighted: {
    background: "var(--color-highlight-soft)",
    borderRadius: "var(--radius-sm)",
  } as React.CSSProperties,
  highlight: {
    padding: "2px 4px",
    background: "var(--color-accent-soft)",
    borderRadius: "2px",
    cursor: "pointer",
  } as React.CSSProperties,
  pagePara: {
    margin: "var(--space-2) 0",
  } as React.CSSProperties,
  citationRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: "var(--space-2)",
    marginTop: "var(--space-3)",
    paddingTop: "var(--space-3)",
    borderTop: "1px solid var(--color-border)",
  } as React.CSSProperties,
};
