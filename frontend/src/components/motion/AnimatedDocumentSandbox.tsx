"use client";

import React, { useState } from "react";

export function AnimatedDocumentSandbox() {
  const [activeTab, setActiveTab] = useState<"simplified" | "original">("simplified");
  const [highlightedPassage, setHighlightedPassage] = useState(false);

  return (
    <div
      id="example"
      className="editorial-card hero-sandbox"
      style={{
        maxWidth: "1000px",
        margin: "0 auto",
        textAlign: "left",
        overflow: "hidden",
        position: "relative",
      }}
    >
      {/* ── Top Bar: Mode Switcher & Disclaimer ── */}
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

        {/* Tab Controls */}
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
              padding: "5px 14px",
              fontSize: "var(--text-xs)",
              fontWeight: "var(--font-medium)",
              borderRadius: "var(--radius-sm)",
              border: "none",
              cursor: "pointer",
              background: activeTab === "simplified" ? "var(--color-accent-soft)" : "transparent",
              color: activeTab === "simplified" ? "var(--color-accent)" : "var(--color-text-secondary)",
              transition: "all var(--duration-fast) var(--ease-default)",
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
              padding: "5px 14px",
              fontSize: "var(--text-xs)",
              fontWeight: "var(--font-medium)",
              borderRadius: "var(--radius-sm)",
              border: "none",
              cursor: "pointer",
              background: activeTab === "original" ? "var(--color-accent-soft)" : "transparent",
              color: activeTab === "original" ? "var(--color-accent)" : "var(--color-text-secondary)",
              transition: "all var(--duration-fast) var(--ease-default)",
            }}
          >
            Sample notice excerpt
          </button>
        </div>
      </div>

      {/* ── Sandbox Content Container ── */}
      <div style={{ padding: "var(--space-6)", position: "relative" }}>
        {activeTab === "simplified" ? (
          <div className="sandbox-tab-content anim-fade-in">
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
                  Passport Renewal (Sample) &middot; Illustrative plain-language breakdown with page citations
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
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#15803d" }} />
                3 demo citations
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
              {/* Card 1: Documents */}
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

              {/* Card 2: Fees & Timelines */}
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
                  राजश्व र समयसीमा (Fees & Timeline)
                </h4>
                <ul
                  style={{
                    fontSize: "var(--text-xs)",
                    color: "var(--color-text-secondary)",
                    lineHeight: "1.7",
                    paddingLeft: "var(--space-4)",
                  }}
                >
                  <li>साधारण सेवा (३४ पृष्ठ): रु ५,०००/- (जिल्लाबाट)</li>
                  <li>द्रुत सेवा: रु १०,०००/- (राहदानी विभाग, काठमाडौँबाट)</li>
                  <li>म्याद समाप्त हुनुभन्दा १ वर्ष अगावै नवीकरण गर्न सकिनेछ</li>
                </ul>
              </div>
            </div>

            {/* Interactive Grounded Citation Preview */}
            <div
              className={`citation-preview-box ${highlightedPassage ? "is-pulsing" : ""}`}
              onClick={() => setHighlightedPassage(!highlightedPassage)}
              style={{
                padding: "var(--space-4)",
                background: "var(--color-doc-surface)",
                border: "1px solid var(--color-citation-border)",
                borderRadius: "var(--radius-md)",
                cursor: "pointer",
                transition: "border-color 0.2s ease, box-shadow 0.2s ease",
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
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M4 2a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H4zm0 1h8a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" />
                  </svg>
                  Sample Grounded Passage &middot; Page 1, Section 2.1
                </span>
                <span
                  style={{
                    fontSize: "var(--text-xs)",
                    color: "var(--color-text-tertiary)",
                    textDecoration: "underline",
                  }}
                >
                  {highlightedPassage ? "Source passage highlighted" : "Click to spotlight source"}
                </span>
              </div>
              <blockquote
                style={{
                  fontFamily: "var(--font-devanagari)",
                  fontSize: "var(--text-sm)",
                  color: "var(--color-text-primary)",
                  lineHeight: "var(--leading-relaxed)",
                  fontStyle: "normal",
                  paddingLeft: "var(--space-3)",
                  borderLeft: "2px solid var(--color-accent)",
                }}
              >
                &ldquo;...साधारण राहदानी नवीकरण प्रयोजनका लागि निवेदक स्वयं उपस्थित भई पुरानो
                राहदानीको सक्कल तथा नेपाली नागरिकता प्रमाणपत्रको सक्कल पेश गर्नुपर्नेछ।
                राष्ट्रिय परिचयपत्र नम्बर अनिवार्य गरिएको छ।&rdquo;
              </blockquote>
            </div>
          </div>
        ) : (
          <div className="doc-gazette anim-fade-in" style={{ position: "relative" }}>
            {/* Luminous OCR Laser Scan Sweep Beam */}
            <div className="ocr-scan-beam" aria-hidden="true" />

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
                  नेपाल सरकार &middot; राहदानी विभाग (नमूना प्रारूप)
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
                Sample Notice Excerpt (Illustrative)
              </span>
            </div>

            <p
              className={highlightedPassage ? "ocr-target-highlight" : ""}
              style={{
                fontSize: "var(--text-sm)",
                lineHeight: "1.8",
                color: "var(--color-text-primary)",
                marginBottom: "var(--space-3)",
                padding: "4px 8px",
                borderRadius: "var(--radius-sm)",
                transition: "background 0.3s ease, border-color 0.3s ease",
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
                padding: "4px 8px",
              }}
            >
              जिल्ला प्रशासन कार्यालयहरूबाट ३४ पृष्ठको राहदानीका लागि रु ५,०००/- र
              विभागबाट द्रुत सेवा लिन चाहेमा रु १०,०००/- राजश्व दाखिला गर्नुपर्नेछ।
            </p>
          </div>
        )}
      </div>

      <style jsx>{`
        .hero-sandbox {
          animation: heroFadeUp 0.85s cubic-bezier(0.22, 1, 0.36, 1) 0.32s both;
        }
        .anim-fade-in {
          animation: fadeInTab 0.35s ease-out both;
        }
        @keyframes fadeInTab {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        /* ── Signature OCR Scanning Beam ── */
        .ocr-scan-beam {
          position: absolute;
          left: 0;
          right: 0;
          height: 2px;
          background: linear-gradient(90deg, transparent 0%, var(--color-accent) 50%, transparent 100%);
          box-shadow: 0 0 12px 1px rgba(200, 82, 11, 0.6);
          animation: ocrScanSweep 3.2s ease-in-out infinite alternate;
          pointer-events: none;
          z-index: 10;
        }

        .citation-preview-box:hover {
          border-color: var(--color-accent);
          box-shadow: 0 2px 8px rgba(200, 82, 11, 0.12);
        }
        .citation-preview-box.is-pulsing {
          border-color: var(--color-accent);
          box-shadow: 0 0 0 3px rgba(200, 82, 11, 0.2);
        }
        .ocr-target-highlight {
          background: rgba(200, 82, 11, 0.08);
          border-left: 3px solid var(--color-accent);
        }

        @keyframes heroFadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        @media (prefers-reduced-motion: reduce) {
          .hero-sandbox,
          .anim-fade-in,
          .ocr-scan-beam {
            animation: none !important;
            opacity: 1 !important;
            transform: none !important;
          }
          .ocr-scan-beam {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
}
