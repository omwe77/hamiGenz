"use client";

import React, { useCallback } from "react";
import Image from "next/image";
import { ViewerPage, Citation, SearchMatch } from "@/lib/types";

type Props = {
  docId: string;
  pages: ViewerPage[];
  onTextHighlight: (text: string) => void;
  citationsByPage: Map<number, Citation[]>;
  searchMatches: SearchMatch[];
  /** Page currently holding the active citation highlight */
  activeCitationPage: number | null;
  /** Index of the active search match (into `searchMatches`) */
  activeSearchMatchIdx: number | null;
  onActiveSearchMatchChange: (idx: number | null) => void;
};

type Segment =
  | { kind: "text"; text: string }
  | { kind: "cite"; text: string }
  | { kind: "match"; text: string };

type Range = { start: number; end: number; kind: "cite" | "match" };

/**
 * Find the best highlightable occurrence of a citation excerpt inside a
 * paragraph. Chunk text is whitespace-normalized on the backend, so long
 * excerpts rarely appear verbatim in raw page text — fall back to
 * progressively shorter word-boundary snippets so the user still gets
 * a useful highlight.
 */
function findExcerptRange(para: string, excerpt: string): Range | null {
  const lowerPara = para.toLowerCase();
  let snippet = excerpt.toLowerCase().trim();
  if (!snippet) return null;
  while (snippet.length >= 12) {
    const idx = lowerPara.indexOf(snippet);
    if (idx !== -1) {
      return { start: idx, end: idx + snippet.length, kind: "cite" };
    }
    // Shrink to ~60% and cut at a word boundary to avoid mid-word fragments
    let next = snippet.slice(0, Math.floor(snippet.length * 0.6));
    const cut = next.lastIndexOf(" ");
    if (cut > 0) next = next.slice(0, cut);
    if (next === snippet) break;
    snippet = next;
  }
  return null;
}

/**
 * Split one paragraph into text/cite/match segments for rendering.
 * `excerpts` are citation excerpts to highlight (case-insensitive).
 * `match` is the active search match: `highlight_start/end` are offsets into
 * `match.text` (a context window). We align by locating the matched term
 * itself inside the paragraph, which is robust to window/paragraph drift.
 */
export function buildSegments(
  para: string,
  excerpts: string[],
  match: SearchMatch | null
): Segment[] {
  const ranges: Range[] = [];

  for (const ex of excerpts) {
    const r = findExcerptRange(para, ex);
    if (r) ranges.push(r);
  }

  if (match && match.page != null) {
    const mText = match.text ?? "";
    if (
      match.highlight_start >= 0 &&
      match.highlight_end > match.highlight_start &&
      match.highlight_end <= mText.length
    ) {
      const term = mText.slice(match.highlight_start, match.highlight_end).trim();
      if (term) {
        const lowerPara = para.toLowerCase();
        const termLower = term.toLowerCase();
        let idx = lowerPara.indexOf(termLower);
        while (idx !== -1) {
          ranges.push({ start: idx, end: idx + termLower.length, kind: "match" });
          idx = lowerPara.indexOf(termLower, idx + termLower.length);
        }
      }
    }
  }

  if (ranges.length === 0) return [{ kind: "text", text: para }];

  // Sort by start; on ties, matches come first (they take precedence)
  ranges.sort((a, b) => a.start - b.start || (a.kind === "match" ? -1 : 1));

  const merged: Range[] = [];
  for (const r of ranges) {
    const last = merged[merged.length - 1];
    if (last && r.start < last.end) {
      if (r.kind === "match" && last.kind === "cite") {
        // Split the cite range around the match
        if (last.start < r.start) {
          merged[merged.length - 1] = { ...last, end: r.start };
          merged.push({ ...r });
          if (last.end > r.end) merged.push({ start: r.end, end: last.end, kind: "cite" });
        } else {
          merged.push({ ...r });
        }
      } else {
        last.end = Math.max(last.end, r.end);
      }
    } else {
      merged.push({ ...r });
    }
  }
  merged.sort((a, b) => a.start - b.start);

  const segments: Segment[] = [];
  let pos = 0;
  for (const r of merged) {
    if (r.start > pos) segments.push({ kind: "text", text: para.slice(pos, r.start) });
    segments.push({ kind: r.kind, text: para.slice(r.start, r.end) });
    pos = r.end;
  }
  if (pos < para.length) segments.push({ kind: "text", text: para.slice(pos) });
  return segments;
}

export default function DocumentViewer({
  pages,
  onTextHighlight,
  citationsByPage,
  searchMatches,
  activeCitationPage,
  activeSearchMatchIdx,
  onActiveSearchMatchChange,
}: Props) {
  const activeMatch =
    activeSearchMatchIdx != null
      ? searchMatches[activeSearchMatchIdx] ?? null
      : null;

  // Scroll the active search match into view whenever the ref attaches.
  const scrollToMatch = useCallback(
    (el: HTMLElement | null) => {
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    },
    []
  );

  const handleSelection = useCallback(() => {
    setTimeout(() => {
      const sel = window.getSelection();
      const text = sel?.toString().trim();
      if (text && text.length > 1) {
        onTextHighlight(text);
      }
    }, 40);
  }, [onTextHighlight]);

  const goToMatch = useCallback(
    (idx: number) => {
      if (idx >= 0 && idx < searchMatches.length) {
        onActiveSearchMatchChange(idx);
      }
    },
    [searchMatches.length, onActiveSearchMatchChange]
  );

  if (pages.length === 0) {
    return (
      <div style={styles.empty}>
        <p>No pages found for this document.</p>
      </div>
    );
  }

  return (
    <div style={styles.viewer}>
      {pages.map((page) => {
        const pageCitations = citationsByPage.get(page.page_num) ?? [];
        const excerpts = pageCitations.map((c) => c.excerpt);
        const isCitedPage = activeCitationPage === page.page_num;
        const pageMatch =
          activeMatch && activeMatch.page === page.page_num ? activeMatch : null;

        return (
          <div key={page.page_num} style={styles.pageWrapper}>
            <div
              id={`page-${page.page_num}`}
              style={{
                ...styles.pageContent,
                ...(isCitedPage ? styles.pageContentActive : {}),
              }}
            >
              <div style={styles.pageHeader}>
                <span style={styles.pageLabel}>Page {page.page_num}</span>
                <span style={styles.pageWords}>{page.word_count} words</span>
                {page.has_image && page.image_url && (
                  <span style={styles.pageHasImage}>scanned page</span>
                )}
              </div>

              {page.has_image && page.image_url && (
                <Image
                  src={page.image_url}
                  alt={`Page ${page.page_num} scanned image`}
                  style={styles.pageImage}
                  width={800}
                  height={1100}
                  unoptimized
                  loading="lazy"
                />
              )}

              <div
                style={{
                  ...styles.pageText,
                  ...(isCitedPage ? styles.pageTextHighlighted : {}),
                }}
                onMouseUp={handleSelection}
                onTouchEnd={handleSelection}
              >
                {page.text
                  ? page.text.split("\n").map((para, i) => {
                      if (!para.trim()) return null;
                      const segments = buildSegments(para, excerpts, pageMatch);
                      return (
                        <p key={i} style={styles.pagePara}>
                          {segments.map((seg, j) => {
                            if (seg.kind === "cite") {
                              return (
                                <mark
                                  key={j}
                                  style={styles.citeHighlight}
                                  title="Evidence from your document"
                                >
                                  {seg.text}
                                </mark>
                              );
                            }
                            if (seg.kind === "match") {
                              return (
                                <mark key={j} ref={scrollToMatch} style={styles.searchHighlight}>
                                  {seg.text}
                                </mark>
                              );
                            }
                            return <span key={j}>{seg.text}</span>;
                          })}
                        </p>
                      );
                    })
                  : page.has_image
                    ? "(Scanned page — see image above. OCR found no extractable text.)"
                    : "(No text on this page.)"}
              </div>

              {pageCitations.length > 0 && (
                <div style={styles.citationRow}>
                  {pageCitations.map((c, i) => (
                    <span
                      key={i}
                      style={styles.citationNote}
                      title={c.excerpt.slice(0, 160)}
                    >
                      {c.excerpt.slice(0, 80)}
                      {c.excerpt.length > 80 ? "…" : ""}
                    </span>
                  ))}
                </div>
              )}

              {pageMatch && activeSearchMatchIdx != null && (
                <div style={styles.searchNav}>
                  <button
                    style={styles.searchNavBtn}
                    onClick={() => goToMatch((activeSearchMatchIdx ?? 0) - 1)}
                    disabled={activeSearchMatchIdx === 0}
                  >
                    ← Prev match
                  </button>
                  <span style={styles.searchNavInfo}>
                    Match {activeSearchMatchIdx + 1} of {searchMatches.length}
                  </span>
                  <button
                    style={styles.searchNavBtn}
                    onClick={() => goToMatch((activeSearchMatchIdx ?? 0) + 1)}
                    disabled={activeSearchMatchIdx === searchMatches.length - 1}
                  >
                    Next match →
                  </button>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  empty: {
    padding: "var(--space-8)",
    textAlign: "center",
    color: "var(--color-text-tertiary)",
    fontSize: "var(--text-sm)",
  },
  viewer: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-4)",
  },
  pageWrapper: {
    display: "flex",
    flexDirection: "column",
  },
  pageContent: {
    background: "var(--color-doc-surface)",
    border: "1px solid var(--color-doc-border)",
    borderRadius: "var(--radius-xl)",
    padding: "var(--space-6)",
    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02)",
    transition: "border-color var(--duration-fast) var(--ease-default), box-shadow var(--duration-fast) var(--ease-default)",
  } as React.CSSProperties,
  pageContentActive: {
    borderColor: "var(--color-citation-border)",
    boxShadow: "0 0 0 3px var(--color-citation), 0 4px 12px rgba(245, 158, 11, 0.12)",
  } as React.CSSProperties,
  pageHeader: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-3)",
    marginBottom: "var(--space-4)",
    paddingBottom: "var(--space-3)",
    borderBottom: "1px solid var(--color-doc-border)",
    flexWrap: "wrap",
  } as React.CSSProperties,
  pageLabel: {
    fontFamily: "var(--font-serif)",
    fontSize: "var(--text-base)",
    fontWeight: "var(--font-bold)",
    color: "var(--color-text-primary)",
  } as React.CSSProperties,
  pageWords: {
    fontSize: "11px",
    letterSpacing: "0.02em",
    color: "var(--color-text-tertiary)",
  } as React.CSSProperties,
  pageHasImage: {
    fontSize: "11px",
    fontWeight: "var(--font-medium)",
    color: "var(--color-info)",
    background: "var(--color-evidence)",
    padding: "2px 8px",
    borderRadius: "var(--radius-full)",
    border: "1px solid var(--color-evidence-border)",
  } as React.CSSProperties,
  pageImage: {
    width: "100%",
    height: "auto",
    maxHeight: "600px",
    objectFit: "contain",
    border: "1px solid var(--color-doc-border)",
    borderRadius: "var(--radius-md)",
    marginBottom: "var(--space-4)",
    background: "#ffffff",
  } as React.CSSProperties,
  pageText: {
    fontFamily: "var(--font-devanagari)",
    fontSize: "0.9375rem", /* 15px */
    lineHeight: 1.85,
    color: "var(--color-text-primary)",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  } as React.CSSProperties,
  pageTextHighlighted: {
    background: "rgba(245, 158, 11, 0.08)",
    borderRadius: "var(--radius-sm)",
  } as React.CSSProperties,
  pagePara: {
    margin: "var(--space-3) 0",
  } as React.CSSProperties,
  citeHighlight: {
    background: "var(--color-citation)",
    borderBottom: "2px solid var(--color-citation-border)",
    borderRadius: "2px",
    padding: "2px 4px",
    color: "var(--color-citation-text)",
    fontWeight: "var(--font-medium)",
  } as React.CSSProperties,
  searchHighlight: {
    background: "var(--color-accent-soft)",
    borderBottom: "2px solid var(--color-accent)",
    borderRadius: "2px",
    padding: "2px 3px",
  } as React.CSSProperties,
  citationRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: "var(--space-2)",
    marginTop: "var(--space-3)",
    paddingTop: "var(--space-3)",
    borderTop: "1px solid var(--color-border)",
  },
  citationNote: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
    background: "var(--color-bg-alt)",
    padding: "4px 8px",
    borderRadius: "var(--radius-sm)",
    maxWidth: "100%",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  searchNav: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "var(--space-3)",
    marginTop: "var(--space-3)",
    paddingTop: "var(--space-3)",
    borderTop: "1px solid var(--color-border)",
    flexWrap: "wrap",
  },
  searchNavBtn: {
    position: "relative",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "44px",
    padding: "var(--space-2) var(--space-4)",
    background: "var(--color-bg-alt)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-text-secondary)",
    cursor: "pointer",
    transition: "background var(--duration-fast) var(--ease-default), border-color var(--duration-fast) var(--ease-default)",
  },
  searchNavInfo: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
  },
};
