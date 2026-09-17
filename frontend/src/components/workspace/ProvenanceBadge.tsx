"use client";

import React from "react";
import type { GroundingReport } from "@/lib/types";

// ── Types ──────────────────────────────────────────────────────────────
type Props = {
  provenance: "document" | "general_ai" | "mixed";
  grounding: GroundingReport | null;
};

const BADGES = {
  document: {
    label: "YOUR DOCUMENT",
    bg: "#dcfce7",
    fg: "#166534",
    border: "#86efac",
  },
  general_ai: {
    label: "GENERAL AI",
    bg: "#fef3c7",
    fg: "#92400e",
    border: "#fde68a",
  },
  mixed: {
    label: "MIXED",
    bg: "#f3e8ff",
    fg: "#6b21a8",
    border: "#d8b4fe",
  },
};

export default function ProvenanceBadge({ provenance, grounding }: Props) {
  const badge = BADGES[provenance] || BADGES.general_ai;

  // Derive confidence sub-label from the full verification report
  let confidenceLabel = "";
  const band = grounding?.confidence_band;
  const score = grounding?.confidence_score;
  if (band === "HIGH") confidenceLabel = score != null ? `All claims supported (${score})` : "All claims supported";
  else if (band === "MEDIUM") confidenceLabel = score != null ? `Partially supported (${score})` : "Partially supported";
  else if (band === "LOW") confidenceLabel = score != null ? `Insufficient evidence (${score})` : "Insufficient evidence";

  // Warning from grounding
  let warningHtml = "";
  if (grounding?.contradiction_found) {
    const claims = grounding.contradiction_claims || [];
    warningHtml = `Claims conflict with evidence: ${claims.join("; ")}`;
  } else if (grounding?.warning) {
    warningHtml = grounding.warning;
  } else if (confidenceLabel === "Insufficient evidence") {
    warningHtml = "Some claims could not be verified from the available source.";
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "var(--space-2)",
          padding: "var(--space-1) var(--space-3)",
          background: badge.bg,
          color: badge.fg,
          border: "1px solid " + badge.border,
          borderRadius: "var(--radius-md)",
          fontSize: "var(--text-xs)",
          fontWeight: "var(--font-bold)",
          letterSpacing: "0.03em",
        }}
      >
        <span
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            background: badge.fg,
          }}
        />
        {badge.label}
      </div>
      {confidenceLabel && (
        <div
          style={{
            fontSize: "var(--text-xs)",
            color: grounding?.overall_confidence === "LOW" ? "#dc2626" : "var(--color-text-secondary)",
          }}
        >
          {confidenceLabel}
        </div>
      )}
      {warningHtml && (
        <div
          style={{
            fontSize: "var(--text-xs)",
            color: "#dc2626",
            background: "#fef2f2",
            padding: "var(--space-1) var(--space-2)",
            borderRadius: "var(--radius-sm)",
            border: "1px solid #fecaca",
          }}
        >
          {warningHtml}
        </div>
      )}
    </div>
  );
}
