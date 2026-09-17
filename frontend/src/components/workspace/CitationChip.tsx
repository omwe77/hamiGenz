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
      style={{
        ...styles.btn,
        ...(active && styles.btnActive),
      }}
      onClick={onClick}
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
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
    display: "inline-flex",
    alignItems: "center",
    gap: "var(--space-1)",
    padding: "var(--space-1) var(--space-3)",
    background: "var(--color-evidence)",
    color: "var(--color-info)",
    border: "1px solid var(--color-evidence-border)",
    borderRadius: "var(--radius-full)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-medium)",
    cursor: "pointer",
    transition: "all 0.15s ease",
  } as React.CSSProperties,
  btnActive: {
    background: "var(--color-accent)",
    color: "white",
    borderColor: "var(--color-accent)",
  } as React.CSSProperties,
  label: {
    whiteSpace: "nowrap",
  } as React.CSSProperties,
};
