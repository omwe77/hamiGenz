import React from "react";

type Citation = { page: number; excerpt: string };
type Props = {
  citation: Citation;
  active: boolean;
  onClick: () => void;
};

export default function CitationChip({ citation, active, onClick }: Props) {
  return (
    <button
      className="touch-target-expand"
      style={{
        ...styles.btn,
        ...(active ? styles.btnActive : {}),
      }}
      onClick={onClick}
      aria-label={`Jump to citation on page ${citation.page}`}
      aria-pressed={active}
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }} aria-hidden="true">
        <rect x="3" y="3" width="7" height="7" rx="1" fill="currentColor" />
        <rect x="14" y="3" width="7" height="7" rx="1" fill="currentColor" />
        <rect x="3" y="14" width="7" height="7" rx="1" fill="currentColor" />
        <rect x="14" y="14" width="7" height="7" rx="1" fill="currentColor" />
      </svg>
      <span style={styles.label}>Page {citation.page}</span>
    </button>
  );
}

const styles = {
  btn: {
    position: "relative",
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    padding: "6px 12px",
    minHeight: "36px",
    background: "var(--color-citation)",
    color: "var(--color-citation-text)",
    border: "1px solid var(--color-citation-border)",
    borderRadius: "var(--radius-full)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-semibold)",
    cursor: "pointer",
    boxShadow: "0 1px 2px rgba(245, 158, 11, 0.15)",
    transition: "all var(--duration-fast) var(--ease-default)",
  } as React.CSSProperties,
  btnActive: {
    background: "var(--color-accent)",
    color: "#ffffff",
    borderColor: "var(--color-accent)",
    boxShadow: "0 0 0 3px var(--color-accent-soft), var(--shadow-sm)",
    transform: "translateY(-1px)",
  } as React.CSSProperties,
  label: {
    whiteSpace: "nowrap",
    letterSpacing: "0.01em",
  } as React.CSSProperties,
};
