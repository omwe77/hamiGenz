"use client";

import React, { useRef } from "react";
import { useSectionScrollProgress, useEntranceReveals } from "@/lib/motion";
import { EvidenceTrail } from "./EvidenceTrail";

export function CapabilitiesSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const scrollProgress = useSectionScrollProgress(sectionRef, {
    offsetStart: 0.85,
    offsetEnd: 0.25,
  });

  useEntranceReveals(".capability-card-reveal", {
    rootMargin: "0px 0px -10% 0px",
    threshold: 0.15,
    staggerDelayMs: 90,
  });

  return (
    <section
      id="capabilities"
      ref={sectionRef}
      style={{
        position: "relative",
        padding: "var(--space-16) var(--space-6)",
        maxWidth: "var(--max-width)",
        margin: "0 auto",
      }}
    >
      {/* Header */}
      <div style={{ textAlign: "center", maxWidth: "620px", margin: "0 auto var(--space-12)" }}>
        <span className="section-label">Platform Capabilities</span>
        <h2
          style={{
            fontSize: "var(--text-3xl)",
            fontWeight: "var(--font-bold)",
            letterSpacing: "-0.02em",
            marginTop: "var(--space-2)",
            marginBottom: "var(--space-3)",
          }}
        >
          Built specifically for civic documents.
        </h2>
        <p style={{ fontSize: "var(--text-base)", color: "var(--color-text-secondary)", lineHeight: "1.6" }}>
          General-purpose AI frequently misinterprets regional administrative language.
          hamiGenZ is structured around three precise, verifiable steps.
        </p>
      </div>

      {/* Grid container with progressive SVG evidence trail */}
      <div
        className="caps-grid-wrap"
        style={{
          position: "relative",
        }}
      >
        <EvidenceTrail progress={scrollProgress} />

        <div
          className="caps-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "var(--space-6)",
          }}
        >
          {/* Step 01: Read */}
          <div
            className="editorial-card capability-card-reveal"
            style={{
              padding: "var(--space-6)",
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-3)",
              position: "relative",
            }}
          >
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "var(--radius-md)",
                background: "var(--color-bg-alt)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-accent)",
              }}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
            </div>

            <span className="section-label" style={{ color: "var(--color-accent)" }}>
              Step 01
            </span>
            <h3 style={{ fontSize: "var(--text-xl)", fontWeight: "var(--font-bold)" }}>
              Read
            </h3>
            <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", lineHeight: "1.6" }}>
              Extracts text and table layout from scanned notices, circulars, or PDF forms—even with
              low-contrast municipal stamps, faint seals, or complex Devanagari typography.
            </p>
          </div>

          {/* Step 02: Understand */}
          <div
            className="editorial-card capability-card-reveal"
            style={{
              padding: "var(--space-6)",
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-3)",
              position: "relative",
            }}
          >
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "var(--radius-md)",
                background: "var(--color-bg-alt)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-accent)",
              }}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>

            <span className="section-label" style={{ color: "var(--color-accent)" }}>
              Step 02
            </span>
            <h3 style={{ fontSize: "var(--text-xl)", fontWeight: "var(--font-bold)" }}>
              Understand
            </h3>
            <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", lineHeight: "1.6" }}>
              Translates dense bureaucratic phrasing, legal provisos, and fee schedules
              into clear, action-oriented checklists in plain Nepali, Romanized Nepali, or English.
            </p>
          </div>

          {/* Step 03: Verify */}
          <div
            className="editorial-card capability-card-reveal"
            style={{
              padding: "var(--space-6)",
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-3)",
              position: "relative",
            }}
          >
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "var(--radius-md)",
                background: "var(--color-bg-alt)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-accent)",
              }}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <polyline points="9 12 11 14 15 10" />
              </svg>
            </div>

            <span className="section-label" style={{ color: "var(--color-accent)" }}>
              Step 03
            </span>
            <h3 style={{ fontSize: "var(--text-xl)", fontWeight: "var(--font-bold)" }}>
              Verify
            </h3>
            <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", lineHeight: "1.6" }}>
              Strict provenance grounding. Every fact, fee, and requirement links directly
              to the exact page and paragraph of the official document, flagging any ambiguous clauses.
            </p>
          </div>
        </div>
      </div>

      <style jsx>{`
        .capability-card-reveal {
          opacity: 0;
          transform: translateY(24px);
          transition: opacity 0.65s cubic-bezier(0.22, 1, 0.36, 1),
                      transform 0.65s cubic-bezier(0.22, 1, 0.36, 1),
                      box-shadow 0.25s ease;
        }
        .capability-card-reveal.visible {
          opacity: 1;
          transform: translateY(0);
        }
        .capability-card-reveal:hover {
          transform: translateY(-4px);
          box-shadow: 0 8px 24px rgba(28, 25, 23, 0.08);
        }
        @media (max-width: 840px) {
          .caps-grid {
            grid-template-columns: 1fr !important;
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .capability-card-reveal {
            opacity: 1 !important;
            transform: none !important;
            transition: none !important;
          }
          .capability-card-reveal:hover {
            transform: none !important;
          }
        }
      `}</style>
    </section>
  );
}
