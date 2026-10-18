"use client";

import React from "react";
import Link from "next/link";

export function HeroTypography() {
  return (
    <div className="hero-typography-wrap">
      {/* 1. Civic Badge */}
      <div className="hero-anim-item hero-entry--badge">
        <div className="editorial-badge" id="hero-badge">
          <span className="badge-dot" />
          <span>Evidence-based civic document assistance &middot; Nepal</span>
        </div>
      </div>

      {/* 2. Cinematic Headline */}
      <div className="hero-anim-item hero-entry--title">
        <h1
          className="hero-title"
          id="hero-title"
          style={{
            fontSize: "clamp(2.5rem, 5.2vw, 4rem)",
            fontWeight: "var(--font-bold)",
            letterSpacing: "-0.035em",
            color: "var(--color-text-primary)",
            lineHeight: "1.12",
            marginBottom: "var(--space-5)",
          }}
        >
          Understand Nepal&apos;s{" "}
          <span className="hero-headline-accent">official documents</span> with cited certainty.
        </h1>
      </div>

      {/* 3. Subtitle / Mission Statement */}
      <div className="hero-anim-item hero-entry--sub">
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
          Upload a notice, gazette, or circular. Get an instant plain-language explanation
          in Nepali or English, backed by exact paragraph references you can verify.
        </p>
      </div>

      {/* 4. Action CTAs */}
      <div className="hero-anim-item hero-entry--ctas">
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
            className="btn-editorial"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "var(--space-2)",
              background: "var(--color-accent)",
              color: "#ffffff",
              fontSize: "var(--text-base)",
              fontWeight: "var(--font-semibold)",
              padding: "13px 26px",
              borderRadius: "var(--radius-md)",
              boxShadow: "0 2px 6px rgba(200, 82, 11, 0.25)",
              transition: "transform var(--duration-fast) var(--ease-default), background var(--duration-fast) var(--ease-default)",
            }}
          >
            Open interactive workspace
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
              padding: "13px 24px",
              borderRadius: "var(--radius-md)",
              transition: "border-color var(--duration-fast) var(--ease-default), background var(--duration-fast) var(--ease-default)",
            }}
          >
            Examine sample document
          </a>
        </div>
      </div>

      <style jsx>{`
        .hero-typography-wrap {
          max-width: 840px;
          margin: 0 auto;
          position: relative;
          z-index: 1;
        }
        .hero-headline-accent {
          background: linear-gradient(135deg, var(--color-accent) 0%, #b45309 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          display: inline-block;
        }
        .badge-dot {
          display: inline-block;
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background: #15803d;
          margin-right: 6px;
        }

        /* ── Choreographed Hero Cascade ── */
        .hero-anim-item {
          animation: heroFadeUp 0.8s cubic-bezier(0.22, 1, 0.36, 1) both;
        }
        .hero-entry--badge {
          animation-delay: 0.05s;
          margin-bottom: var(--space-4);
        }
        .hero-entry--title {
          animation-delay: 0.16s;
        }
        .hero-entry--sub {
          animation-delay: 0.28s;
        }
        .hero-entry--ctas {
          animation-delay: 0.40s;
        }

        @keyframes heroFadeUp {
          from {
            opacity: 0;
            transform: translateY(18px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @media (prefers-reduced-motion: reduce) {
          .hero-anim-item {
            animation: none !important;
            opacity: 1 !important;
            transform: none !important;
          }
          .hero-headline-accent {
            -webkit-text-fill-color: var(--color-accent);
          }
        }
      `}</style>
    </div>
  );
}
