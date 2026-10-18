"use client";

import { useRef, useEffect, useState } from "react";
import EvidenceTrail from "./EvidenceTrail";
import { useGlobalScrollProgress } from "@/lib/motion";

const CAPABILITIES = [
  {
    id: "read",
    step: "01",
    title: "Read",
    headline: "Multilingual Document Parsing",
    description:
      "Processes scanned PDFs, images, and structured civic documents written in Nepali, Devanagari, or mixed scripts with high fidelity.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
        <polyline points="10 9 9 9 8 9"/>
      </svg>
    ),
    delay: 0,
  },
  {
    id: "understand",
    step: "02",
    title: "Understand",
    headline: "Evidence-Grounded Answers",
    description:
      "Grounds every response in retrieved passages from the source document. No hallucination—every claim is traceable to a specific page and paragraph.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        <line x1="11" y1="8" x2="11" y2="14"/>
        <line x1="8" y1="11" x2="14" y2="11"/>
      </svg>
    ),
    delay: 0.15,
  },
  {
    id: "verify",
    step: "03",
    title: "Verify",
    headline: "Cited, Traceable, Trustworthy",
    description:
      "Generates explanations with inline citations that link directly to the original source passage, so citizens and officials can audit every answer independently.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
    ),
    delay: 0.30,
  },
];

export default function CapabilitiesSection() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);
  const scrollProgress = useGlobalScrollProgress();

  // Intersection observer for card reveals
  useEffect(() => {
    const observers: IntersectionObserver[] = [];
    cardRefs.current.forEach((card) => {
      if (!card) return;
      const obs = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            card.classList.add("visible");
            obs.disconnect();
          }
        },
        { threshold: 0.15 }
      );
      obs.observe(card);
      observers.push(obs);
    });
    return () => observers.forEach((o) => o.disconnect());
  }, []);

  return (
    <section
      id="capabilities"
      ref={containerRef}
      style={{
        padding: "var(--space-16) var(--space-6) var(--space-20)",
        maxWidth: "var(--max-width)",
        margin: "0 auto",
      }}
    >
      {/* Section header */}
      <div className="section-reveal" style={{ textAlign: "center", maxWidth: "600px", margin: "0 auto var(--space-12)" }}>
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
          From raw document to verified answer.
        </h2>
        <p style={{ color: "var(--color-text-secondary)", lineHeight: "1.65" }}>
          A three-stage pipeline that makes complex civic documents understandable
          and every answer independently verifiable.
        </p>
      </div>

      {/* Cards with SVG trail above them */}
      <div className="caps-grid-wrap">
        <EvidenceTrail progress={scrollProgress} />

        <div
          className="caps-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "var(--space-6)",
            position: "relative",
            zIndex: 1,
          }}
        >
          {CAPABILITIES.map((cap, i) => (
            <div
              key={cap.id}
              ref={(el) => { cardRefs.current[i] = el; }}
              className="capability-card-reveal editorial-card"
              style={{ transitionDelay: `${cap.delay}s` }}
            >
              {/* Step badge */}
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-4)" }}>
                <span
                  style={{
                    fontSize: "var(--text-xs)",
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-accent)",
                    letterSpacing: "0.08em",
                    fontWeight: "var(--font-semibold)",
                  }}
                >
                  {cap.step}
                </span>
                <span
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "32px",
                    height: "32px",
                    borderRadius: "6px",
                    background: "var(--color-surface-raised)",
                    color: "var(--color-accent)",
                    border: "1px solid var(--color-border)",
                  }}
                >
                  {cap.icon}
                </span>
              </div>

              <h3 style={{ fontSize: "var(--text-lg)", fontWeight: "var(--font-semibold)", marginBottom: "var(--space-1)" }}>
                {cap.headline}
              </h3>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", lineHeight: "1.7" }}>
                {cap.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
