"use client";

import { useState } from "react";
import Link from "next/link";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"simplified" | "original">("simplified");

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-bg)",
        color: "var(--color-text-primary)",
        fontFamily: "var(--font-sans)",
      }}
    >
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
          }}
        >
          <div style={{ maxWidth: "800px", margin: "0 auto" }}>
            <div
              className="editorial-badge"
              style={{ marginBottom: "var(--space-4)" }}
              id="hero-badge"
            >
              <span>Evidence-based civic document assistance</span>
            </div>

            <h1
              className="hero-title"
              id="hero-title"
              style={{
                fontSize: "clamp(2.4rem, 5vw, 3.75rem)",
                fontWeight: "var(--font-bold)",
                letterSpacing: "-0.03em",
                color: "var(--color-text-primary)",
                marginBottom: "var(--space-4)",
                lineHeight: "1.15",
              }}
            >
              Understand Nepal&apos;s official documents.
            </h1>

            <p
              id="hero-sub"
              style={{
                fontSize: "clamp(1.05rem, 2vw, 1.25rem)",
                color: "var(--color-text-secondary)",
                lineHeight: "var(--leading-relaxed)",
                maxWidth: "680px",
                margin: "0 auto var(--space-8)",
              }}
            >
              Upload a notice, form or letter. Get a plain-language explanation and
              find the passage that supports it.
            </p>

            <div
              id="hero-ctas"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "var(--space-4)",
                flexWrap: "wrap",
                marginBottom: "var(--space-12)",
              }}
            >
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
                  padding: "12px 24px",
                  borderRadius: "var(--radius-md)",
                  boxShadow: "0 2px 4px rgba(200, 82, 11, 0.2)",
                  transition: "background var(--duration-fast) var(--ease-default)",
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

              <a
                href="#example"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "var(--space-2)",
                  background: "var(--color-surface)",
                  color: "var(--color-text-primary)",
                  border: "1px solid var(--color-border)",
                  fontSize: "var(--text-base)",
                  fontWeight: "var(--font-medium)",
                  padding: "12px 22px",
                  borderRadius: "var(--radius-md)",
                }}
              >
                View an example
              </a>
            </div>
          </div>

          {/* ── Interactive Before / After Example Sandbox ──── */}
          <div
            id="example"
            className="editorial-card"
            style={{
              maxWidth: "1000px",
              margin: "0 auto",
              textAlign: "left",
              overflow: "hidden",
            }}
          >
            {/* Disclaimer & Mode Switcher Bar */}
            <div
              style={{
                padding: "var(--space-3) var(--space-5)",
                background: "var(--color-bg-alt)",
                borderBottom: "1px solid var(--color-border)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: "var(--space-3)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span
                  style={{
                    display: "inline-block",
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    background: "#d97706",
                  }}
                />
                <span
                  style={{
                    fontSize: "var(--text-xs)",
                    fontWeight: "var(--font-medium)",
                    color: "var(--color-text-secondary)",
                  }}
                >
                  Illustrative example &mdash; not official information.
                </span>
              </div>

              <div
                style={{
                  display: "inline-flex",
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  padding: "2px",
                }}
                role="tablist"
                aria-label="Document view toggle"
              >
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === "simplified"}
                  onClick={() => setActiveTab("simplified")}
                  style={{
                    padding: "4px 12px",
                    fontSize: "var(--text-xs)",
                    fontWeight: "var(--font-medium)",
                    borderRadius: "var(--radius-sm)",
                    border: "none",
                    cursor: "pointer",
                    background: activeTab === "simplified" ? "var(--color-accent-soft)" : "transparent",
                    color: activeTab === "simplified" ? "var(--color-accent)" : "var(--color-text-secondary)",
                  }}
                >
                  Plain-language guide
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === "original"}
                  onClick={() => setActiveTab("original")}
                  style={{
                    padding: "4px 12px",
                    fontSize: "var(--text-xs)",
                    fontWeight: "var(--font-medium)",
                    borderRadius: "var(--radius-sm)",
                    border: "none",
                    cursor: "pointer",
                    background: activeTab === "original" ? "var(--color-accent-soft)" : "transparent",
                    color: activeTab === "original" ? "var(--color-accent)" : "var(--color-text-secondary)",
                  }}
                >
                  Original document notice
                </button>
              </div>
            </div>

            {/* Sandbox Content View */}
            <div style={{ padding: "var(--space-6)" }}>
              {activeTab === "simplified" ? (
                <div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      marginBottom: "var(--space-4)",
                      flexWrap: "wrap",
                      gap: "var(--space-2)",
                    }}
                  >
                    <div>
                      <span className="section-label" style={{ color: "var(--color-accent)" }}>
                        Plain-Language Summary
                      </span>
                      <h3
                        style={{
                          fontSize: "var(--text-xl)",
                          fontWeight: "var(--font-bold)",
                          marginTop: "2px",
                        }}
                      >
                        राहदानी नवीकरणका लागि आवश्यक कागजात र शुल्क
                      </h3>
                      <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>
                        Passport Renewal Notice &middot; Plain summary extracted with page citations
                      </p>
                    </div>

                    <div
                      style={{
                        fontSize: "var(--text-xs)",
                        color: "var(--color-success)",
                        background: "var(--color-verified)",
                        padding: "4px 10px",
                        borderRadius: "var(--radius-full)",
                        fontWeight: "var(--font-medium)",
                        border: "1px solid var(--color-verified-border)",
                      }}
                    >
                      3 passages verified
                    </div>
                  </div>

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                      gap: "var(--space-4)",
                      marginBottom: "var(--space-6)",
                    }}
                  >
                    <div
                      style={{
                        padding: "var(--space-4)",
                        background: "var(--color-bg-alt)",
                        borderRadius: "var(--radius-md)",
                        border: "1px solid var(--color-border)",
                      }}
                    >
                      <h4
                        style={{
                          fontSize: "var(--text-sm)",
                          fontWeight: "var(--font-semibold)",
                          marginBottom: "var(--space-2)",
                          color: "var(--color-text-primary)",
                        }}
                      >
                        आवश्यक कागजात (Required Documents)
                      </h4>
                      <ul
                        style={{
                          fontSize: "var(--text-xs)",
                          color: "var(--color-text-secondary)",
                          lineHeight: "1.7",
                          paddingLeft: "var(--space-4)",
                        }}
                      >
                        <li>पुरानो राहदानीको सक्कल प्रति (Original old passport)</li>
                        <li>नागरिकता प्रमाणपत्रको सक्कल र प्रतिलिपि</li>
                        <li>राष्ट्रिय परिचयपत्र नम्बर वा कार्ड (NID Number)</li>
                        <li>अनलाइन आवेदन फारामको प्रमाणित प्रिन्ट</li>
                      </ul>
                    </div>

                    <div
                      style={{
                        padding: "var(--space-4)",
                        background: "var(--color-bg-alt)",
                        borderRadius: "var(--radius-md)",
                        border: "1px solid var(--color-border)",
                      }}
                    >
                      <h4
                        style={{
                          fontSize: "var(--text-sm)",
                          fontWeight: "var(--font-semibold)",
                          marginBottom: "var(--space-2)",
                          color: "var(--color-text-primary)",
                        }}
                      >
                        दस्तुर तथा समयसीमा (Fees &amp; Timeline)
                      </h4>
                      <ul
                        style={{
                          fontSize: "var(--text-xs)",
                          color: "var(--color-text-secondary)",
                          lineHeight: "1.7",
                          paddingLeft: "var(--space-4)",
                        }}
                      >
                        <li>साधारण ३४ पृष्ठ: रु ५,०००/- (जिल्ला प्रशासन कार्यालय)</li>
                        <li>द्रुत सेवा (काठमाडौँ विभाग): रु १०,०००/-</li>
                        <li>म्याद समाप्त हुनुभन्दा १ वर्ष अगावै नवीकरण गर्न सकिनेछ</li>
                      </ul>
                    </div>
                  </div>

                  {/* Grounded Citation Preview */}
                  <div
                    style={{
                      padding: "var(--space-4)",
                      background: "var(--color-doc-surface)",
                      border: "1px solid var(--color-citation-border)",
                      borderRadius: "var(--radius-md)",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: "var(--space-2)",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "var(--text-xs)",
                          fontWeight: "var(--font-semibold)",
                          color: "var(--color-citation-text)",
                        }}
                      >
                        Verified Source Passage &middot; Page 1, Section 2.1
                      </span>
                      <span
                        style={{
                          fontSize: "var(--text-xs)",
                          color: "var(--color-text-tertiary)",
                        }}
                      >
                        Exact match
                      </span>
                    </div>
                    <blockquote
                      style={{
                        fontFamily: "var(--font-devanagari)",
                        fontSize: "var(--text-sm)",
                        color: "var(--color-text-primary)",
                        lineHeight: "var(--leading-relaxed)",
                        fontStyle: "normal",
                      }}
                    >
                      &ldquo;...साधारण राहदानी नवीकरण प्रयोजनका लागि निवेदक स्वयं उपस्थित भई पुरानो
                      राहदानीको सक्कल तथा नेपाली नागरिकता प्रमाणपत्रको सक्कल पेश गर्नुपर्नेछ।
                      राष्ट्रिय परिचयपत्र नम्बर अनिवार्य गरिएको छ।&rdquo;
                    </blockquote>
                  </div>
                </div>
              ) : (
                <div className="doc-gazette">
                  <div className="doc-gazette-header">
                    <div>
                      <span
                        style={{
                          fontSize: "var(--text-xs)",
                          fontWeight: "var(--font-bold)",
                          letterSpacing: "0.05em",
                          color: "var(--color-nepal-red)",
                        }}
                      >
                        नेपाल सरकार &middot; राहदानी विभाग
                      </span>
                      <div
                        style={{
                          fontSize: "var(--text-xs)",
                          color: "var(--color-text-tertiary)",
                        }}
                      >
                        सूचना सङ्ख्या: ०८०-८१/०४ &middot; प्रकाशित मिति: २०८०/०६/१५
                      </div>
                    </div>
                    <span
                      style={{
                        fontSize: "var(--text-xs)",
                        padding: "2px 8px",
                        background: "var(--color-bg-alt)",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--color-border)",
                      }}
                    >
                      Official Notice Excerpt
                    </span>
                  </div>

                  <p
                    style={{
                      fontSize: "var(--text-sm)",
                      lineHeight: "1.8",
                      color: "var(--color-text-primary)",
                      marginBottom: "var(--space-3)",
                    }}
                  >
                    सर्वसाधारणको जानकारीका लागि यो सूचना प्रकाशित गरिएको छ। वि.सं. २०८० कार्तिक १
                    गतेदेखि लागु हुने गरी विद्युतीय राहदानी (e-Passport) नवीकरण तथा नयाँ जारी गर्दा
                    राष्ट्रिय परिचयपत्र (NID) अनिवार्य गरिएको छ।
                  </p>
                  <p
                    style={{
                      fontSize: "var(--text-sm)",
                      lineHeight: "1.8",
                      color: "var(--color-text-primary)",
                    }}
                  >
                    जिल्ला प्रशासन कार्यालयहरूबाट ३४ पृष्ठको राहदानीका लागि रु ५,०००/- र विभागबाट
                    द्रुत सेवा लिन चाहेमा रु १०,०००/- राजश्व दाखिला गर्नुपर्नेछ।
                  </p>
                </div>
              )}
            </div>
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

        {/* ── 3 Core Capabilities: Read, Understand, Verify ─── */}
        <section
          id="capabilities"
          style={{
            padding: "var(--space-16) var(--space-6)",
            maxWidth: "var(--max-width)",
            margin: "0 auto",
          }}
        >
          <div style={{ textAlign: "center", maxWidth: "600px", margin: "0 auto var(--space-12)" }}>
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
            <p style={{ fontSize: "var(--text-base)", color: "var(--color-text-secondary)" }}>
              General-purpose AI frequently misinterprets regional administrative language.
              hamiGenZ is structured around three precise steps.
            </p>
          </div>

          <div
            className="caps-grid"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: "var(--space-6)",
            }}
          >
            {/* Capability 1: Read */}
            <div
              className="editorial-card"
              style={{
                padding: "var(--space-6)",
                display: "flex",
                flexDirection: "column",
                gap: "var(--space-3)",
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
                Extracts text and table layout from scanned notices, letters, or PDF forms—even with
                low-contrast stamps, faint seals, or complex Devanagari typography.
              </p>
            </div>

            {/* Capability 2: Understand */}
            <div
              className="editorial-card"
              style={{
                padding: "var(--space-6)",
                display: "flex",
                flexDirection: "column",
                gap: "var(--space-3)",
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
                Translates dense bureaucratic phrasing, legal conditions, and administrative rules
                into clear, step-by-step checklists in plain Nepali and English.
              </p>
            </div>

            {/* Capability 3: Verify */}
            <div
              className="editorial-card"
              style={{
                padding: "var(--space-6)",
                display: "flex",
                flexDirection: "column",
                gap: "var(--space-3)",
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
        </section>

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
