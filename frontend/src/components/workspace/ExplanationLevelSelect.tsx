"use client";

import React, { useState } from "react";

type Props = {
  value: "original" | "simple" | "very_simple";
  onChange: (v: "original" | "simple" | "very_simple") => void;
};

const OPTIONS = [
  { value: "original", label: "Original", hint: "Preserve formal wording, explain meaning faithfully" },
  { value: "simple", label: "Simple", hint: "Everyday language, exact meaning preserved" },
  { value: "very_simple", label: "Very Simple", hint: "Short sentences, every term explained inline" },
];

export default function ExplanationLevelSelect({ value, onChange }: Props) {
  return (
    <div style={styles.wrapper}>
      {OPTIONS.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            style={{
              ...styles.btn,
              ...(active && styles.btnActive),
            }}
            onClick={() => onChange(opt.value)}
            title={opt.hint}
          >
            <span style={styles.btnLabel}>{opt.label}</span>
            {active && <span style={styles.btnDot} />}
          </button>
        );
      })}
    </div>
  );
}

const styles = {
  wrapper: {
    display: "flex",
    gap: "var(--space-2)",
    flexWrap: "wrap",
  } as React.CSSProperties,
  btn: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-2)",
    padding: "var(--space-2) var(--space-3)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-text-secondary)",
    cursor: "pointer",
    transition: "all 0.15s ease",
  } as React.CSSProperties,
  btnActive: {
    background: "var(--color-accent)",
    borderColor: "var(--color-accent)",
    color: "white",
  } as React.CSSProperties,
  btnLabel: {
    fontSize: "var(--text-sm)",
  } as React.CSSProperties,
  btnDot: {
    width: "6px",
    height: "6px",
    borderRadius: "50%",
    background: "currentColor",
  } as React.CSSProperties,
};
