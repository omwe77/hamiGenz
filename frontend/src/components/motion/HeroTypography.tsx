"use client";

import Link from "next/link";

/**
 * HeroTypography
 * Cinematic staggered-entry hero text. All animation via globals.css
 * .hero-anim-item class; no styled-jsx needed.
 */
export default function HeroTypography() {
  return (
    <div className="hero-typography-wrap">
      <div id="prov-anchor-hero" className="editorial-badge hero-anim-item hero-entry--badge">
        <span className="badge-dot" aria-hidden="true" />
        <span>Evidence-based civic document assistance</span>
      </div>

      <h1
        className="hero-anim-item hero-entry--title"
        style={{
          fontSize: "clamp(2.25rem, 5vw, 3.75rem)",
          fontWeight: "var(--font-bold)",
          letterSpacing: "-0.03em",
          lineHeight: "1.08",
          marginBottom: "var(--space-5)",
          color: "var(--color-text-primary)",
        }}
      >
        Understand documents.{" "}
        <span className="hero-headline-accent">Verify the answer.</span>
      </h1>

      <p
        className="hero-anim-item hero-entry--sub"
        style={{
          fontSize: "clamp(1rem, 2vw, 1.2rem)",
          color: "var(--color-text-secondary)",
          lineHeight: "1.65",
          maxWidth: "600px",
          margin: "0 auto var(--space-8)",
        }}
      >
        hamiGenZ reads complex Nepali civic and legal documents, grounds every
        answer in cited source passages, and presents the information in clear,
        accessible language—with full provenance you can verify.
      </p>

      <div
        className="hero-anim-item hero-entry--ctas"
        style={{
          display: "flex",
          gap: "var(--space-3)",
          justifyContent: "center",
          flexWrap: "wrap",
        }}
      >
        <Link
          href="/workspace"
          className="btn-editorial"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            padding: "0.7rem 1.6rem",
            background: "var(--color-accent)",
            color: "#ffffff",
            borderRadius: "6px",
            fontWeight: "var(--font-semibold)",
            fontSize: "var(--text-sm)",
            letterSpacing: "0.01em",
            textDecoration: "none",
            transition: "background 0.18s ease, transform 0.18s ease",
          }}
        >
          Open Workspace
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        </Link>
        <a
          href="#capabilities"
          style={{
            display: "inline-flex",
            alignItems: "center",
            padding: "0.7rem 1.4rem",
            border: "1px solid var(--color-border)",
            borderRadius: "6px",
            fontWeight: "var(--font-medium)",
            fontSize: "var(--text-sm)",
            color: "var(--color-text-secondary)",
            textDecoration: "none",
          }}
        >
          See how it works
        </a>
      </div>
    </div>
  );
}
