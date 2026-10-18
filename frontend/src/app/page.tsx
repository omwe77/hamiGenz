"use client";

import { useState } from "react";
import Link from "next/link";
import { ScrollDepthIndicator } from "@/components/motion/ScrollDepthIndicator";
import { AmbientDepthCanvas } from "@/components/motion/AmbientDepthCanvas";
import HeroTypography from "@/components/motion/HeroTypography";
import AnimatedDocumentSandbox from "@/components/motion/AnimatedDocumentSandbox";
import CapabilitiesSection from "@/components/motion/CapabilitiesSection";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"simplified" | "original">("simplified");

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-bg)",
        color: "var(--color-text-primary)",
        fontFamily: "var(--font-sans)",
        position: "relative",
        overflowX: "hidden",
      }}
    >
      {/* ── Ambient Background ──────────────────────────────────── */}
      <AmbientDepthCanvas />

      {/* ── Scroll Depth Indicator ──────────────────────────────── */}
      <ScrollDepthIndicator />

      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* ── Top Navigation ─────────────────────────────────── */}
      <header
        className="glass-header"
        id="main-nav"
        style={{
          height: "var(--header-height)",
          padding: "0 var(--space-6)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
          <Link
            href="/"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-2)",
              fontWeight: "var(--font-bold)",
              fontSize: "var(--text-xl)",
              color: "var(--color-text-primary)",
              letterSpacing: "-0.02em",
            }}
          >
            <svg
              width="32"
              height="32"
              viewBox="0 0 32 32"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <rect width="32" height="32" rx="7" fill="#c8520b" />
              <path
                d="M9 10h14M9 16h14M9 22h10"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <circle cx="24" cy="22" r="3.5" fill="white" fillOpacity="0.9" />
            </svg>
            hamiGenZ
          </Link>

          <span className="editorial-badge nav-status-badge">
            <span
              style={{
                width: "7px",
                height: "7px",
                borderRadius: "50%",
                background: "var(--color-success)",
                display: "inline-block",
              }}
            />
            <span>Civic Document Reader &middot; Nepal</span>
          </span>
        </div>

        <nav
          style={{ display: "flex", alignItems: "center", gap: "var(--space-6)" }}
          aria-label="Primary navigation"
        >
          <div className="nav-text-links" style={{ display: "flex", gap: "var(--space-5)" }}>
            <a
              href="#capabilities"
              style={{
                fontSize: "var(--text-sm)",
                color: "var(--color-text-secondary)",
                fontWeight: "var(--font-medium)",
              }}
            >
              Capabilities
            </a>
            <a
              href="#example"
              style={{
                fontSize: "var(--text-sm)",
                color: "var(--color-text-secondary)",
                fontWeight: "var(--font-medium)",
              }}
            >
              Example
            </a>
            <a
              href="#how-it-works"
              style={{
                fontSize: "var(--text-sm)",
                color: "var(--color-text-secondary)",
                fontWeight: "var(--font-medium)",
              }}
            >
              How it works
            </a>
          </div>

          <Link
            href="/workspace"
            className="touch-target-expand"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "var(--space-2)",
              background: "var(--color-accent)",
              color: "#ffffff",
              fontSize: "var(--text-sm)",
              fontWeight: "var(--font-semibold)",
              padding: "8px 18px",
              borderRadius: "var(--radius-md)",
              transition: "background var(--duration-fast) var(--ease-default)",
            }}
          >
            Open workspace
            <svg
              width="14"
              height="14"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M3 8h10M9 4l4 4-4 4" />
            </svg>
          </Link>
        </nav>
      </header>

      {/* ── Main Content ──────────────────────────────────── */}
      <main id="main-content">
        {/* ── Hero Section ─────────────────────────────────── */}
        <section
          style={{
            padding: "var(--space-16) var(--space-6) var(--space-12)",
            maxWidth: "var(--max-width)",
            margin: "0 auto",
            textAlign: "center",
            position: "relative",
            zIndex: 1,
          }}
        >
          <HeroTypography />

          {/* Animated Document Sandbox */}
          <div style={{ marginTop: "var(--space-12)" }}>
            <AnimatedDocumentSandbox />
          </div>
        </section>


        {/* ── Civic Ledger / Values Strip ───────────────────── */}
        <section className="ledger-strip" aria-label="Core operational principles">
          <div className="container">
            <div className="ledger-grid">
              <div>
                <span className="section-label">Evidence Grounding</span>
                <h4 style={{ fontSize: "var(--text-base)", fontWeight: "var(--font-semibold)", marginTop: "4px" }}>
                  Every claim is cited
                </h4>
                <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)", marginTop: "4px" }}>
                  Answers cite the exact page and paragraph so you can verify the original text yourself.
                </p>
              </div>

              <div>
                <span className="section-label">Privacy First</span>
                <h4 style={{ fontSize: "var(--text-base)", fontWeight: "var(--font-semibold)", marginTop: "4px" }}>
                  Your documents stay private
                </h4>
                <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)", marginTop: "4px" }}>
                  Uploaded files remain within your active workspace and are never used to train public models.
                </p>
              </div>

              <div>
                <span className="section-label">Contradiction Alerts</span>
                <h4 style={{ fontSize: "var(--text-base)", fontWeight: "var(--font-semibold)", marginTop: "4px" }}>
                  Discrepancy detection
                </h4>
                <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)", marginTop: "4px" }}>
                  The engine flags conflicting requirements, superseded notices, and outdated dates.
                </p>
              </div>

              <div>
                <span className="section-label">Bilingual Accessibility</span>
                <h4 style={{ fontSize: "var(--text-base)", fontWeight: "var(--font-semibold)", marginTop: "4px" }}>
                  Nepali &amp; English
                </h4>
                <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)", marginTop: "4px" }}>
                  Read explanations in clear conversational Nepali, Romanized Nepali, or English.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ── Capabilities Section ─────────────────────────── */}
        <CapabilitiesSection />


        {/* ── How It Works ──────────────────────────────────── */}
        <section
          id="how-it-works"
          style={{
            padding: "var(--space-12) var(--space-6) var(--space-16)",
            maxWidth: "var(--max-width)",
            margin: "0 auto",
          }}
        >
          <div style={{ textAlign: "center", maxWidth: "600px", margin: "0 auto var(--space-12)" }}>
            <span className="section-label">Workflow</span>
            <h2
              style={{
                fontSize: "var(--text-3xl)",
                fontWeight: "var(--font-bold)",
                letterSpacing: "-0.02em",
                marginTop: "var(--space-2)",
              }}
            >
              How to use the workspace.
            </h2>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "var(--space-6)",
            }}
          >
            <div
              style={{
                borderLeft: "2px solid var(--color-accent)",
                paddingLeft: "var(--space-4)",
              }}
            >
              <div
                style={{
                  fontSize: "var(--text-xs)",
                  fontWeight: "var(--font-bold)",
                  color: "var(--color-accent)",
                  marginBottom: "var(--space-1)",
                }}
              >
                1. Select or upload
              </div>
              <h4 style={{ fontSize: "var(--text-base)", fontWeight: "var(--font-semibold)", marginBottom: "var(--space-2)" }}>
                Choose a document
              </h4>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", lineHeight: "1.6" }}>
                Select from verified reference documents or upload your own notice, citizenship form, or passport directive.
              </p>
            </div>

            <div
              style={{
                borderLeft: "2px solid var(--color-border)",
                paddingLeft: "var(--space-4)",
              }}
            >
              <div
                style={{
                  fontSize: "var(--text-xs)",
                  fontWeight: "var(--font-bold)",
                  color: "var(--color-text-tertiary)",
                  marginBottom: "var(--space-1)",
                }}
              >
                2. Ask in plain language
              </div>
              <h4 style={{ fontSize: "var(--text-base)", fontWeight: "var(--font-semibold)", marginBottom: "var(--space-2)" }}>
                Ask your question
              </h4>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", lineHeight: "1.6" }}>
                Type your question in Nepali, Romanized Nepali, or English, or click one of the suggested prompts for common requirements.
              </p>
            </div>

            <div
              style={{
                borderLeft: "2px solid var(--color-border)",
                paddingLeft: "var(--space-4)",
              }}
            >
              <div
                style={{
                  fontSize: "var(--text-xs)",
                  fontWeight: "var(--font-bold)",
                  color: "var(--color-text-tertiary)",
                  marginBottom: "var(--space-1)",
                }}
              >
                3. Inspect the citation
              </div>
              <h4 style={{ fontSize: "var(--text-base)", fontWeight: "var(--font-semibold)", marginBottom: "var(--space-2)" }}>
                Check the original page
              </h4>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", lineHeight: "1.6" }}>
                Click any citation tag to view the highlighted bounding box and passage in the side-by-side document viewer.
              </p>
            </div>
          </div>
        </section>

        {/* ── Final Call to Action ──────────────────────────── */}
        <section
          id="final-cta-section"
          style={{
            background: "var(--color-surface)",
            borderTop: "1px solid var(--color-border)",
            borderBottom: "1px solid var(--color-border)",
            padding: "var(--space-16) var(--space-6)",
            textAlign: "center",
          }}
        >
          <div style={{ maxWidth: "600px", margin: "0 auto" }}>
            <h2
              style={{
                fontSize: "var(--text-3xl)",
                fontWeight: "var(--font-bold)",
                letterSpacing: "-0.02em",
                marginBottom: "var(--space-3)",
              }}
            >
              Ready to examine a document?
            </h2>
            <p
              style={{
                fontSize: "var(--text-base)",
                color: "var(--color-text-secondary)",
                marginBottom: "var(--space-8)",
              }}
            >
              Try the interactive workspace with preloaded public notices or your own files.
              No registration required.
            </p>

            <Link
              href="/workspace"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "var(--space-2)",
                background: "var(--color-accent)",
                color: "#ffffff",
                fontSize: "var(--text-base)",
                fontWeight: "var(--font-semibold)",
                padding: "12px 28px",
                borderRadius: "var(--radius-md)",
                boxShadow: "0 2px 4px rgba(200, 82, 11, 0.2)",
              }}
            >
              Open workspace
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M3 8h10M9 4l4 4-4 4" />
              </svg>
            </Link>
          </div>
        </section>
      </main>

      {/* ── Footer ────────────────────────────────────────── */}
      <footer
        style={{
          padding: "var(--space-12) var(--space-6)",
          maxWidth: "var(--max-width)",
          margin: "0 auto",
          fontSize: "var(--text-xs)",
          color: "var(--color-text-tertiary)",
          lineHeight: "1.7",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: "var(--space-6)",
            borderBottom: "1px solid var(--color-border)",
            paddingBottom: "var(--space-8)",
            marginBottom: "var(--space-6)",
          }}
        >
          <div style={{ maxWidth: "420px" }}>
            <div
              style={{
                fontWeight: "var(--font-bold)",
                fontSize: "var(--text-base)",
                color: "var(--color-text-primary)",
                marginBottom: "var(--space-2)",
              }}
            >
              hamiGenZ
            </div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              A civic clarification tool for Nepal&apos;s administrative notices, official forms,
              and public directives. Built on Open Knowledge Format (OKF v0.2).
            </p>
          </div>

          <div style={{ display: "flex", gap: "var(--space-8)", flexWrap: "wrap" }}>
            <div>
              <div
                style={{
                  fontWeight: "var(--font-semibold)",
                  color: "var(--color-text-primary)",
                  marginBottom: "var(--space-2)",
                }}
              >
                Navigation
              </div>
              <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
                <li>
                  <Link href="/workspace" style={{ color: "var(--color-text-secondary)" }}>
                    Workspace
                  </Link>
                </li>
                <li>
                  <a href="#capabilities" style={{ color: "var(--color-text-secondary)" }}>
                    Capabilities
                  </a>
                </li>
                <li>
                  <a href="#example" style={{ color: "var(--color-text-secondary)" }}>
                    Sample Notice
                  </a>
                </li>
              </ul>
            </div>

            <div>
              <div
                style={{
                  fontWeight: "var(--font-semibold)",
                  color: "var(--color-text-primary)",
                  marginBottom: "var(--space-2)",
                }}
              >
                Principles
              </div>
              <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
                <li>Local &amp; private processing</li>
                <li>Verifiable citation links</li>
                <li>Contradiction detection</li>
              </ul>
            </div>
          </div>
        </div>

        <p style={{ maxWidth: "800px" }}>
          <strong>Civic Disclaimer:</strong> hamiGenZ provides informational explanations to help citizens
          navigate complex documentation. It does not provide legal representation, certified legal advice,
          or official government determinations. For binding legal matters, please consult the issuing ministry,
          district administration office, or a licensed advocate.
        </p>
      </footer>
    </div>
  );
}
