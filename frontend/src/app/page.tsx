"use client";

import { useEffect, useState } from "react";

/* ── Homepage with anime.js scroll storytelling ───────── */
export default function Home() {
  const [animeReady, setAnimeReady] = useState(false);

  useEffect(() => {
    import("animejs").then((mod) => {
      (window as any).anime = mod.animate;
      setAnimeReady(true);
    });
  }, []);

  useEffect(() => {
    if (!animeReady) return;

    const animeFn = (window as any).anime;
    if (!animeFn) return;

    const heroTitle = document.getElementById("hero-title");
    const heroSub = document.getElementById("hero-sub");
    const heroCtas = document.getElementById("hero-ctas");
    const finalCta = document.getElementById("final-cta");

    if (heroTitle && heroSub) {
      animeFn({
        targets: [heroTitle, heroSub],
        opacity: [0, 1],
        translateY: [30, 0],
        duration: 800,
        easing: "easeOutCubic",
        delay: (el: any, i: number) => i * 120,
      });
    }

    if (heroCtas) {
      animeFn({
        targets: heroCtas,
        opacity: [0, 1],
        scale: [0.92, 1],
        duration: 600,
        easing: "easeOutCubic",
        delay: 500,
      });
    }

    /* ── Scroll-driven story (Intersection Observer) ─── */
    const steps = document.querySelectorAll("[data-scroll-step]");
    const scanline = document.getElementById("scanline");

    if (!steps.length) return;

    const stepRefs = Array.from(steps).map((el) => el as HTMLElement);
    const stepObs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const el = entry.target as HTMLElement;
            const step = parseInt(el.dataset.scrollStep || "0");
            const delay = step * 180;

            // Animate each step in when it enters viewport
            animeFn({
              targets: el,
              opacity: [0, 1],
              translateY: [30, 0],
              scale: [0.97, 1],
              duration: 700,
              delay: delay,
              easing: "easeOutCubic",
              children: true,
            });

            // Special: scanline movement
            if (el.id === "doc-card" && scanline) {
              animeFn({
                targets: scanline,
                translateY: [-20, 400],
                opacity: [0, 1, 0],
                duration: 2200,
                delay: 300,
                easing: "linear",
                loop: false,
              });
            }

            // Extracted box items stagger
            if (el.id === "extracted-box") {
              const items = el.querySelectorAll("[data-extract-item]");
              animeFn({
                targets: items,
                opacity: [0, 1],
                translateY: [16, 0],
                scale: [0.94, 1],
                duration: 500,
                delay: (el2: any, i: number) => i * 100,
                easing: "easeOutCubic",
              });
            }

            // Simple explanation items stagger
            if (el.id === "simple-box") {
              const items = el.querySelectorAll("[data-simple-item]");
              animeFn({
                targets: items,
                opacity: [0, 1],
                translateY: [16, 0],
                scale: [0.94, 1],
                duration: 500,
                delay: (el2: any, i: number) => i * 120,
                easing: "easeOutCubic",
              });
            }

            // Evidence items stagger
            if (el.id === "evidence-box") {
              const items = el.querySelectorAll("[data-evidence-item]");
              animeFn({
                targets: items,
                opacity: [0, 1],
                translateX: [-12, 0],
                duration: 500,
                delay: (el2: any, i: number) => i * 130,
                easing: "easeOutCubic",
              });
            }

            // Final CTA
            if (el.id === "final-cta") {
              animeFn({
                targets: el,
                opacity: [0, 1],
                scale: [0.97, 1],
                translateY: [20, 0],
                duration: 800,
                easing: "easeOutCubic",
              });
            }

            stepObs.unobserve(el);
          }
        });
      },
      { threshold: 0.25, rootMargin: "0px 0px -40px 0px" }
    );

    stepRefs.forEach((el) => stepObs.observe(el));

    return () => stepObs.disconnect();
  }, [animeReady]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-bg)",
        fontFamily: "var(--font-sans)",
      }}
    >
      {/* ── Navigation ──────────────────────────────────── */}
      <header
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          zIndex: 200,
          transition: "background var(--duration-slow) var(--ease-default), box-shadow var(--duration-slow) var(--ease-default)",
          padding: "0 var(--space-8)",
          height: "var(--header-height)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "transparent",
        }}
        id="main-nav"
      >
        <div
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
        </div>
        <nav
          style={{
            display: "flex",
            alignItems: "center",
            gap: "var(--space-6)",
          }}
        >
          {["Product", "How it works", "Sources", "About"].map((label) => (
            <a
              key={label}
              href={`#${label.toLowerCase().replace(" ", "-")}`}
              style={{
                color: "var(--color-text-secondary)",
                fontSize: "var(--text-sm)",
                fontWeight: "var(--font-medium)",
                transition: "color var(--duration-fast) var(--ease-default)",
              }}
            >
              {label}
            </a>
          ))}
          <a
            href="#open-workspace"
            style={{
              background: "var(--color-accent)",
              color: "white",
              padding: "var(--space-2) var(--space-5)",
              borderRadius: "var(--radius-md)",
              fontSize: "var(--text-sm)",
              fontWeight: "var(--font-semibold)",
              transition: "background var(--duration-fast) var(--ease-default), transform var(--duration-fast) var(--ease-default)",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.background = "var(--color-accent-hover)";
              (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(-1px)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.background = "var(--color-accent)";
              (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(0)";
            }}
          >
            Open hamiGenZ
          </a>
        </nav>
      </header>

      {/* ── Hero ────────────────────────────────────────── */}
      <section
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: "var(--space-24) var(--space-6)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Subtle background grid pattern */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: `linear-gradient(var(--color-border-soft) 1px, transparent 1px),
                              linear-gradient(90deg, var(--color-border-soft) 1px, transparent 1px)`,
            backgroundSize: "60px 60px",
            opacity: 0.4,
            pointerEvents: "none",
          }}
        />

        {/* Soft ambient glow */}
        <div
          style={{
            position: "absolute",
            top: "20%",
            left: "50%",
            transform: "translateX(-50%)",
            width: "600px",
            height: "600px",
            background: "radial-gradient(ellipse, var(--color-accent-soft) 0%, transparent 70%)",
            opacity: 0.5,
            pointerEvents: "none",
          }}
        />

        <div
          style={{
            position: "relative",
            maxWidth: "760px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <div
            id="hero-title"
            style={{
              opacity: 0,
              transform: "translateY(30px)",
              fontFamily: "var(--font-serif)",
              fontSize: "var(--text-6xl)",
              color: "var(--color-text-primary)",
              marginBottom: "var(--space-6)",
              lineHeight: "1.1",
              letterSpacing: "-0.03em",
            }}
          >
            Don&apos;t understand it?{" "}
            <span style={{ color: "var(--color-accent)" }}>Ask hamiGenZ.</span>
          </div>

          <div
            id="hero-sub"
            style={{
              opacity: 0,
              transform: "translateY(30px)",
              color: "var(--color-text-secondary)",
              fontSize: "var(--text-xl)",
              lineHeight: "1.5",
              maxWidth: "560px",
              marginBottom: "var(--space-10)",
            }}
          >
            Upload a document, ask a question, or describe what you need. hamiGenZ reads it,
            explains it simply, and shows you the evidence you can check.
          </div>

          <div
            id="hero-ctas"
            style={{
              opacity: 0,
              transform: "scale(0.92)",
              display: "flex",
              gap: "var(--space-4)",
              flexWrap: "wrap",
              justifyContent: "center",
            }}
          >
            <a
              href="#open-workspace"
              style={{
                background: "var(--color-accent)",
                color: "white",
                padding: "var(--space-4) var(--space-8)",
                borderRadius: "var(--radius-lg)",
                fontSize: "var(--text-lg)",
                fontWeight: "var(--font-semibold)",
                textDecoration: "none",
                boxShadow: "var(--shadow-md)",
                transition: "background var(--duration-fast) var(--ease-default), transform var(--duration-fast) var(--ease-default), box-shadow var(--duration-fast) var(--ease-default)",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.background = "var(--color-accent-hover)";
                (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(-2px)";
                (e.currentTarget as HTMLAnchorElement).style.boxShadow = "var(--shadow-lg)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.background = "var(--color-accent)";
                (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(0)";
                (e.currentTarget as HTMLAnchorElement).style.boxShadow = "var(--shadow-md)";
              }}
            >
              Try hamiGenZ
            </a>
            <a
              href="#story"
              style={{
                color: "var(--color-text-primary)",
                padding: "var(--space-4) var(--space-8)",
                borderRadius: "var(--radius-lg)",
                fontSize: "var(--text-lg)",
                fontWeight: "var(--font-medium)",
                textDecoration: "none",
                border: "1px solid var(--color-border)",
                background: "var(--color-surface)",
                transition: "border-color var(--duration-fast) var(--ease-default), color var(--duration-fast) var(--ease-default), background var(--duration-fast) var(--ease-default)",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--color-accent)";
                (e.currentTarget as HTMLAnchorElement).style.color = "var(--color-accent)";
                (e.currentTarget as HTMLAnchorElement).style.background = "var(--color-accent-soft)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--color-border)";
                (e.currentTarget as HTMLAnchorElement).style.color = "var(--color-text-primary)";
                (e.currentTarget as HTMLAnchorElement).style.background = "var(--color-surface)";
              }}
            >
              See how it works
            </a>
          </div>
        </div>
      </section>

      {/* ── Scroll Story ────────────────────────────────── */}
      <section
        id="story"
        style={{
          padding: "var(--space-24) var(--space-6)",
          maxWidth: "1100px",
          margin: "0 auto",
        }}
      >
        <div
          style={{
            textAlign: "center",
            marginBottom: "var(--space-16)",
          }}
        >
          <h2
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "var(--text-4xl)",
              color: "var(--color-text-primary)",
              marginBottom: "var(--space-4)",
            }}
          >
            How hamiGenZ works
          </h2>
          <p
            style={{
              color: "var(--color-text-secondary)",
              fontSize: "var(--text-lg)",
              maxWidth: "520px",
              margin: "0 auto",
            }}
          >
            Information is complicated. Here&apos;s what happens when you let hamiGenZ understand it for you.
          </p>
        </div>

        {/* Pinned visual + scrolling narrative */}
        <div
          id="scroll-story-wrap"
          style={{
            position: "relative",
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "var(--space-16)",
            alignItems: "start",
          }}
        >
          {/* ── Left: Document visual (stays in view) ──── */}
          <div
            style={{
              position: "sticky",
              top: "calc(var(--header-height) + var(--space-12))",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            {/* Document card */}
            <div
              id="doc-card"
              data-scroll-step="0"
              style={{
                opacity: 0,
                transform: "translateY(30px) scale(0.97)",
                width: "340px",
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-xl)",
                padding: "var(--space-6)",
                boxShadow: "var(--shadow-lg)",
                position: "relative",
              }}
            >
              {/* Scan line */}
              <div
                id="scanline"
                style={{
                  position: "absolute",
                  left: 0,
                  right: 0,
                  top: 0,
                  height: "3px",
                  background: "linear-gradient(90deg, transparent, var(--color-accent), transparent)",
                  opacity: 0,
                  boxShadow: "0 0 8px var(--color-accent)",
                }}
              />

              {/* Document header */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-3)",
                  marginBottom: "var(--space-4)",
                  paddingBottom: "var(--space-4)",
                  borderBottom: "1px solid var(--color-border)",
                }}
              >
                <div
                  style={{
                    width: "28px",
                    height: "28px",
                    background: "var(--color-accent)",
                    borderRadius: "var(--radius-sm)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "white",
                    fontSize: "var(--text-xs)",
                    fontWeight: "var(--font-bold)",
                  }}
                >
                  DP
                </div>
                <div>
                  <p
                    style={{
                      fontWeight: "var(--font-semibold)",
                      fontSize: "var(--text-sm)",
                      color: "var(--color-text-primary)",
                    }}
                  >
                    Department of Passports
                  </p>
                  <p
                    style={{
                      fontSize: "var(--text-xs)",
                      color: "var(--color-text-tertiary)",
                    }}
                  >
                    ePassport Pre-enrollment Form
                  </p>
                </div>
                <span
                  style={{
                    marginLeft: "auto",
                    fontSize: "var(--text-xs)",
                    color: "var(--color-text-tertiary)",
                    background: "var(--color-bg-alt)",
                    padding: "var(--space-1) var(--space-2)",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  Page 1 of 6
                </span>
              </div>

              {/* Fake form content */}
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "var(--space-3)",
                  fontSize: "var(--text-sm)",
                  color: "var(--color-text-secondary)",
                }}
              >
                {[
                  { label: "Applicant Name", value: "___________________________" },
                  { label: "Citizenship No.", value: "___________________________" },
                  { label: "Application Type", value: "☐ Ordinary (34 pages)  ☐ Ordinary (66 pages)" },
                  { label: "Appointment Location", value: "___________________________" },
                  { label: "Select Date", value: "☐ 15 Ashadh 2082" },
                ].map((field) => (
                  <div
                    key={field.label}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "var(--space-1)",
                    }}
                  >
                    <span
                      style={{
                        fontWeight: "var(--font-medium)",
                        fontSize: "var(--text-xs)",
                        color: "var(--color-text-tertiary)",
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                      }}
                    >
                      {field.label}
                    </span>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-text-primary)",
                        borderBottom: "1px dashed var(--color-border)",
                        paddingBottom: "var(--space-1)",
                      }}
                    >
                      {field.value}
                    </span>
                  </div>
                ))}
              </div>

              {/* Status badge */}
              <div
                style={{
                  marginTop: "var(--space-5)",
                  padding: "var(--space-2) var(--space-3)",
                  background: "var(--color-evidence)",
                  border: "1px solid var(--color-evidence-border)",
                  borderRadius: "var(--radius-md)",
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-2)",
                  fontSize: "var(--text-xs)",
                  color: "var(--color-info)",
                }}
              >
                <span style={{ display: "inline-block", width: "6px", height: "6px", background: "var(--color-info)", borderRadius: "50%" }} />
                Document loaded
              </div>
            </div>

            {/* Arrow / connector */}
            <div
              style={{
                marginTop: "var(--space-6)",
                color: "var(--color-text-tertiary)",
                fontSize: "var(--text-sm)",
              }}
            >
              ↓ hamiGenZ reads this
            </div>
          </div>

          {/* ── Right: Narrative steps ─────────────────── */}
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
            {/* Step 1: Document becomes understood */}
            <div
              data-scroll-step="1"
              style={{
                opacity: 0,
                transform: "translateY(30px) scale(0.97)",
                padding: "var(--space-5)",
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-lg)",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-3)",
                  marginBottom: "var(--space-3)",
                }}
              >
                <span
                  style={{
                    width: "24px",
                    height: "24px",
                    background: "var(--color-accent-soft)",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--color-accent)",
                    fontSize: "var(--text-xs)",
                    fontWeight: "var(--font-bold)",
                  }}
                >
                  1
                </span>
                <h3
                  style={{
                    fontSize: "var(--text-lg)",
                    color: "var(--color-text-primary)",
                    fontWeight: "var(--font-semibold)",
                  }}
                >
                  hamiGenZ reads your document
                </h3>
              </div>
              <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                Every page is extracted — text, scanned images, everything.
                hamiGenZ understands Nepali, English, and Romanized Nepali.
              </p>
            </div>

            {/* Step 2: Important fields highlighted */}
            <div
              data-scroll-step="2"
              style={{
                opacity: 0,
                transform: "translateY(30px) scale(0.97)",
                padding: "var(--space-5)",
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-lg)",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-3)",
                  marginBottom: "var(--space-3)",
                }}
              >
                <span
                  style={{
                    width: "24px",
                    height: "24px",
                    background: "var(--color-highlight)",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--color-warning)",
                    fontSize: "var(--text-xs)",
                    fontWeight: "var(--font-bold)",
                  }}
                >
                  2
                </span>
                <h3
                  style={{
                    fontSize: "var(--text-lg)",
                    color: "var(--color-text-primary)",
                    fontWeight: "var(--font-semibold)",
                  }}
                >
                  Key information is found
                </h3>
              </div>
              <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                Deadlines, fees, required documents, form fields — hamiGenZ identifies what matters
                and where it appears in the document.
              </p>
              <div
                style={{
                  marginTop: "var(--space-3)",
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "var(--space-2)",
                }}
              >
                {["Deadline", "Fee amount", "Citizenship copy", "Appointment date"].map(
                  (item) => (
                    <span
                      key={item}
                      style={{
                        background: "var(--color-highlight)",
                        border: "1px solid #fde68a",
                        borderRadius: "var(--radius-full)",
                        padding: "var(--space-1) var(--space-3)",
                        fontSize: "var(--text-xs)",
                        color: "var(--color-warning)",
                        fontWeight: "var(--font-medium)",
                      }}
                    >
                      {item}
                    </span>
                  )
                )}
              </div>
            </div>

            {/* Step 3: Text extracted */}
            <div
              data-scroll-step="3"
              style={{
                opacity: 0,
                transform: "translateY(30px) scale(0.97)",
                padding: "var(--space-5)",
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-lg)",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-3)",
                  marginBottom: "var(--space-3)",
                }}
              >
                <span
                  style={{
                    width: "24px",
                    height: "24px",
                    background: "var(--color-evidence)",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--color-info)",
                    fontSize: "var(--text-xs)",
                    fontWeight: "var(--font-bold)",
                  }}
                >
                  3
                </span>
                <h3
                  style={{
                    fontSize: "var(--text-lg)",
                    color: "var(--color-text-primary)",
                    fontWeight: "var(--font-semibold)",
                  }}
                >
                  Text is extracted & organized
                </h3>
              </div>
              <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                hamiGenZ breaks the document into meaningful pieces and stores them with page references.
                You can always ask “where does it say that?”
              </p>
            </div>

            {/* Step 4: Information reorganized */}
            <div
              id="extracted-box"
              data-scroll-step="4"
              style={{
                opacity: 0,
                transform: "translateY(30px) scale(0.97)",
                padding: "var(--space-5)",
                background: "var(--color-accent-soft)",
                border: "1px solid #fed7aa",
                borderRadius: "var(--radius-lg)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-3)",
                  marginBottom: "var(--space-3)",
                }}
              >
                <span
                  style={{
                    width: "24px",
                    height: "24px",
                    background: "var(--color-accent)",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "white",
                    fontSize: "var(--text-xs)",
                    fontWeight: "var(--font-bold)",
                  }}
                >
                  4
                </span>
                <h3
                  style={{
                    fontSize: "var(--text-lg)",
                    color: "var(--color-text-primary)",
                    fontWeight: "var(--font-semibold)",
                  }}
                >
                  Information is reorganized
                </h3>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "var(--space-3)",
                }}
              >
                {[
                  { label: "Deadline", value: "15 Ashadh 2082" },
                  { label: "Fee", value: "Rs. 500" },
                  { label: "Required", value: "Citizenship copy" },
                  { label: "Form type", value: "Pre-enrollment" },
                ].map((item) => (
                  <div
                    key={item.label}
                    data-extract-item
                    style={{
                      opacity: 0,
                      background: "var(--color-surface)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-md)",
                      padding: "var(--space-3)",
                    }}
                  >
                    <p
                      style={{
                        fontSize: "var(--text-xs)",
                        color: "var(--color-text-tertiary)",
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                        marginBottom: "var(--space-1)",
                      }}
                    >
                      {item.label}
                    </p>
                    <p
                      style={{
                        fontWeight: "var(--font-semibold)",
                        fontSize: "var(--text-sm)",
                        color: "var(--color-text-primary)",
                      }}
                    >
                      {item.value}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Step 5: Simple explanation */}
            <div
              id="simple-box"
              data-scroll-step="5"
              style={{
                opacity: 0,
                transform: "translateY(30px) scale(0.97)",
                padding: "var(--space-5)",
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-lg)",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-3)",
                  marginBottom: "var(--space-3)",
                }}
              >
                <span
                  style={{
                    width: "24px",
                    height: "24px",
                    background: "var(--color-success)",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "white",
                    fontSize: "var(--text-xs)",
                    fontWeight: "var(--font-bold)",
                  }}
                >
                  5
                </span>
                <h3
                  style={{
                    fontSize: "var(--text-lg)",
                    color: "var(--color-text-primary)",
                    fontWeight: "var(--font-semibold)",
                  }}
                >
                  Explained in simple language
                </h3>
              </div>
              <p
                style={{
                  color: "var(--color-text-secondary)",
                  fontSize: "var(--text-sm)",
                  marginBottom: "var(--space-3)",
                }}
              >
                hamiGenZ turns complex government language into clear steps anyone can follow.
              </p>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "var(--space-2)",
                }}
              >
                {[
                  "बुझ्न सक्नुहुन्छ: यो फारम भर्नको लागि आफ्नो नागरिकता प्रतिलिपि र फोटो चाहिएको छ।",
                  "Deadline: Submit before 15 Ashadh 2082.",
                  "Fee: Rs. 500 for ordinary passport.",
                ].map((item, i) => (
                  <p
                    key={i}
                    data-simple-item
                    style={{
                      opacity: 0,
                      fontSize: "var(--text-sm)",
                      color: "var(--color-text-primary)",
                      paddingLeft: "var(--space-4)",
                      borderLeft: "2px solid var(--color-accent)",
                      margin: 0,
                    }}
                  >
                    {item}
                  </p>
                ))}
              </div>
            </div>

            {/* Step 6: Evidence appears */}
            <div
              id="evidence-box"
              data-scroll-step="6"
              style={{
                opacity: 0,
                transform: "translateY(30px) scale(0.97)",
                padding: "var(--space-5)",
                background: "var(--color-evidence)",
                border: "1px solid var(--color-evidence-border)",
                borderRadius: "var(--radius-lg)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-3)",
                  marginBottom: "var(--space-3)",
                }}
              >
                <span
                  style={{
                    width: "24px",
                    height: "24px",
                    background: "var(--color-info)",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "white",
                    fontSize: "var(--text-xs)",
                    fontWeight: "var(--font-bold)",
                  }}
                >
                  ✓
                </span>
                <h3
                  style={{
                    fontSize: "var(--text-lg)",
                    color: "var(--color-text-primary)",
                    fontWeight: "var(--font-semibold)",
                  }}
                >
                  Evidence you can check
                </h3>
              </div>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "var(--space-2)",
                }}
              >
                {[
                  { claim: "Deadline is 15 Ashadh 2082", source: "Page 3" },
                  { claim: "Fee is Rs. 500", source: "Page 2" },
                  { claim: "Requires citizenship copy", source: "Page 1" },
                ].map((item) => (
                  <div
                    key={item.source}
                    data-evidence-item
                    style={{
                      opacity: 0,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "var(--space-3)",
                      background: "var(--color-surface)",
                      border: "1px solid var(--color-evidence-border)",
                      borderRadius: "var(--radius-md)",
                      fontSize: "var(--text-sm)",
                      color: "var(--color-text-primary)",
                    }}
                  >
                    <span>{item.claim}</span>
                    <span
                      style={{
                        background: "var(--color-evidence-border)",
                        color: "var(--color-info)",
                        padding: "var(--space-1) var(--space-2)",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "var(--text-xs)",
                        fontWeight: "var(--font-medium)",
                      }}
                    >
                      {item.source}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Step 7: What action to take */}
            <div
              data-scroll-step="7"
              style={{
                opacity: 0,
                transform: "translateY(30px) scale(0.97)",
                padding: "var(--space-5)",
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-lg)",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-3)",
                  marginBottom: "var(--space-3)",
                }}
              >
                <span
                  style={{
                    width: "24px",
                    height: "24px",
                    background: "var(--color-accent)",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "white",
                    fontSize: "var(--text-xs)",
                    fontWeight: "var(--font-bold)",
                  }}
                >
                  →
                </span>
                <h3
                  style={{
                    fontSize: "var(--text-lg)",
                    color: "var(--color-text-primary)",
                    fontWeight: "var(--font-semibold)",
                  }}
                >
                  What you need to do
                </h3>
              </div>
              <ol
                style={{
                  paddingLeft: "var(--space-6)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "var(--space-2)",
                }}
              >
                {[
                  "Prepare your citizenship copy and photograph.",
                  "Fill in the pre-enrollment form online.",
                  "Choose an appointment date before 15 Ashadh.",
                  "Submit at the selected enrollment center.",
                ].map((step, i) => (
                  <li
                    key={i}
                    style={{
                      fontSize: "var(--text-sm)",
                      color: "var(--color-text-primary)",
                      paddingLeft: "var(--space-2)",
                    }}
                  >
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      </section>

      {/* ── Product Capabilities ───────────────────────── */}
      <section
        id="product"
        style={{
          padding: "var(--space-24) var(--space-6)",
          background: "var(--color-bg-alt)",
        }}
      >
        <div className="container">
          <div style={{ textAlign: "center", marginBottom: "var(--space-16)" }}>
            <h2
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "var(--text-4xl)",
                color: "var(--color-text-primary)",
                marginBottom: "var(--space-4)",
              }}
            >
              What hamiGenZ can do
            </h2>
            <p
              style={{
                color: "var(--color-text-secondary)",
                fontSize: "var(--text-lg)",
                maxWidth: "520px",
                margin: "0 auto",
              }}
            >
              Built for real documents and real questions from people in Nepal.
            </p>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: "var(--space-6)",
            }}
          >
            {[
              {
                title: "Understand any document",
                desc: "Passports, forms, notices, government letters — hamiGenZ reads them all.",
                icon: (
                  <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                    <rect x="4" y="4" width="20" height="20" rx="3" stroke="var(--color-accent)" strokeWidth="1.5" />
                    <path d="M9 10h10M9 14h10M9 18h6" stroke="var(--color-accent)" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                ),
              },
              {
                title: "Ask in your language",
                desc: "English, Nepali script, or Romanized Nepali — hamiGenZ understands all three.",
                icon: (
                  <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                    <circle cx="14" cy="14" r="10" stroke="var(--color-accent)" strokeWidth="1.5" />
                    <path d="M10 14h8M14 10v8" stroke="var(--color-accent)" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                ),
              },
              {
                title: "See the evidence",
                desc: "Every answer shows where it came from — page numbers, document references.",
                icon: (
                  <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                    <path d="M8 18l-4 4 4-4M14 14l4 4-4-4M18 12l4 4-4-4" stroke="var(--color-accent)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    <circle cx="14" cy="14" r="10" stroke="var(--color-accent)" strokeWidth="1.5" />
                  </svg>
                ),
              },
              {
                title: "Simple explanations",
                desc: "Legal and technical terms are explained in plain language you can understand.",
                icon: (
                  <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                    <path d="M14 4l4 8-4 8-4-8z" stroke="var(--color-accent)" strokeWidth="1.5" strokeLinejoin="round" />
                    <path d="M10 14h8M14 10v8" stroke="var(--color-accent)" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                ),
              },
              {
                title: "Form-filling help",
                desc: "Upload a form and ask “how do I fill this?” Get a sample with explanations.",
                icon: (
                  <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                    <rect x="4" y="6" width="20" height="16" rx="2" stroke="var(--color-accent)" strokeWidth="1.5" />
                    <path d="M8 10h12M8 14h8M8 18h10" stroke="var(--color-accent)" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                ),
              },
              {
                title: "Fully local & free",
                desc: "No paid APIs, no cloud dependency. Your documents stay on your machine.",
                icon: (
                  <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                    <circle cx="14" cy="14" r="10" stroke="var(--color-accent)" strokeWidth="1.5" />
                    <path d="M8 14h12M11 11v6M17 11v6" stroke="var(--color-accent)" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                ),
              },
            ].map((cap) => (
              <div
                key={cap.title}
                style={{
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-xl)",
                  padding: "var(--space-6)",
                  boxShadow: "var(--shadow-sm)",
                  transition: "box-shadow var(--duration-normal) var(--ease-default), transform var(--duration-normal) var(--ease-default)",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.boxShadow = "var(--shadow-md)";
                  (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.boxShadow = "var(--shadow-sm)";
                  (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
                }}
              >
                <div
                  style={{
                    width: "48px",
                    height: "48px",
                    background: "var(--color-accent-soft)",
                    borderRadius: "var(--radius-lg)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: "var(--space-4)",
                  }}
                >
                  {cap.icon}
                </div>
                <h3
                  style={{
                    fontSize: "var(--text-lg)",
                    color: "var(--color-text-primary)",
                    fontWeight: "var(--font-semibold)",
                    marginBottom: "var(--space-2)",
                  }}
                >
                  {cap.title}
                </h3>
                <p
                  style={{
                    fontSize: "var(--text-sm)",
                    color: "var(--color-text-secondary)",
                    lineHeight: "1.5",
                  }}
                >
                  {cap.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Interactive Demo ────────────────────────────── */}
      <section
        id="demo"
        style={{
          padding: "var(--space-24) var(--space-6)",
        }}
      >
        <div className="container">
          <div style={{ textAlign: "center", marginBottom: "var(--space-12)" }}>
            <h2
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "var(--text-4xl)",
                color: "var(--color-text-primary)",
                marginBottom: "var(--space-4)",
              }}
            >
              Try it right now
            </h2>
            <p
              style={{
                color: "var(--color-text-secondary)",
                fontSize: "var(--text-lg)",
                maxWidth: "480px",
                margin: "0 auto",
              }}
            >
              Ask a question or upload a document. hamiGenZ is running on your machine — no sign-up needed.
            </p>
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "var(--space-4)",
            }}
          >
            <a
              href="#open-workspace"
              style={{
                background: "var(--color-accent)",
                color: "white",
                padding: "var(--space-5) var(--space-10)",
                borderRadius: "var(--radius-xl)",
                fontSize: "var(--text-xl)",
                fontWeight: "var(--font-semibold)",
                textDecoration: "none",
                boxShadow: "var(--shadow-lg)",
                transition: "background var(--duration-fast) var(--ease-default), transform var(--duration-fast) var(--ease-default), box-shadow var(--duration-fast) var(--ease-default)",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.background = "var(--color-accent-hover)";
                (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(-2px)";
                (e.currentTarget as HTMLAnchorElement).style.boxShadow = "var(--shadow-xl)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.background = "var(--color-accent)";
                (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(0)";
                (e.currentTarget as HTMLAnchorElement).style.boxShadow = "var(--shadow-lg)";
              }}
            >
              Open hamiGenZ →
            </a>
            <p
              style={{
                color: "var(--color-text-tertiary)",
                fontSize: "var(--text-sm)",
              }}
            >
              Connects to the backend on localhost:8000
            </p>
          </div>
        </div>
      </section>

      {/* ── Trust Section ───────────────────────────────── */}
      <section
        id="sources"
        style={{
          padding: "var(--space-24) var(--space-6)",
          background: "var(--color-bg-alt)",
        }}
      >
        <div className="container">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "var(--space-16)",
              alignItems: "start",
            }}
          >
            <div>
              <h2
                style={{
                  fontFamily: "var(--font-serif)",
                  fontSize: "var(--text-3xl)",
                  color: "var(--color-text-primary)",
                  marginBottom: "var(--space-6)",
                }}
              >
                Trust is built in
              </h2>
              <ul
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "var(--space-4)",
                }}
              >
                {[
                  {
                    label: "Based on your document",
                    desc: "Answers come from the document you uploaded, not from vague AI memory.",
                  },
                  {
                    label: "Evidence shown with every claim",
                    desc: "Page numbers and document references appear next to what hamiGenZ says.",
                  },
                  {
                    label: "When it doesn&apos;t know, it says so",
                    desc: "If information isn&apos;t in the document, hamiGenZ tells you rather than guessing.",
                  },
                  {
                    label: "Your data stays local",
                    desc: "Nothing is sent to external APIs. Documents stay on your machine.",
                  },
                ].map((item) => (
                  <li
                    key={item.label}
                    style={{
                      display: "flex",
                      gap: "var(--space-4)",
                      alignItems: "flex-start",
                    }}
                  >
                    <span
                      style={{
                        width: "20px",
                        height: "20px",
                        background: "var(--color-success)",
                        borderRadius: "50%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "white",
                        fontSize: "var(--text-xs)",
                        fontWeight: "var(--font-bold)",
                        flexShrink: 0,
                        marginTop: "2px",
                      }}
                    >
                      ✓
                    </span>
                    <div>
                      <p
                        style={{
                          fontWeight: "var(--font-semibold)",
                          fontSize: "var(--text-base)",
                          color: "var(--color-text-primary)",
                          marginBottom: "var(--space-1)",
                        }}
                      >
                        {item.label}
                      </p>
                      <p
                        style={{
                          fontSize: "var(--text-sm)",
                          color: "var(--color-text-secondary)",
                        }}
                      >
                        {item.desc}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            <div
              style={{
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-xl)",
                padding: "var(--space-8)",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <p
                style={{
                  fontFamily: "var(--font-serif)",
                  fontSize: "var(--text-2xl)",
                  color: "var(--color-text-primary)",
                  marginBottom: "var(--space-6)",
                  textAlign: "center",
                }}
              >
                “I could not verify this from the available sources.”
              </p>
              <p
                style={{
                  color: "var(--color-text-secondary)",
                  fontSize: "var(--text-sm)",
                  textAlign: "center",
                  lineHeight: "1.6",
                }}
              >
                That&apos;s a feature, not a failure. hamiGenZ tells you when it doesn&apos;t have enough
                evidence — so you know when to check the original source yourself.
              </p>
              <div
                style={{
                  marginTop: "var(--space-6)",
                  padding: "var(--space-4)",
                  background: "var(--color-accent-soft)",
                  border: "1px solid #fed7aa",
                  borderRadius: "var(--radius-md)",
                  textAlign: "center",
                  fontSize: "var(--text-sm)",
                  color: "var(--color-accent)",
                  fontWeight: "var(--font-medium)",
                }}
              >
                “I could not verify this from an authoritative source.”
                <br />
                <span style={{ color: "var(--color-text-tertiary)", fontWeight: "var(--font-normal)" }}>
                  — what hamiGenZ says instead of guessing
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────── */}
      <section
        id="how-it-works"
        style={{
          padding: "var(--space-24) var(--space-6)",
        }}
      >
        <div className="container">
          <div style={{ textAlign: "center", marginBottom: "var(--space-16)" }}>
            <h2
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "var(--text-4xl)",
                color: "var(--color-text-primary)",
                marginBottom: "var(--space-4)",
              }}
            >
              How it works
            </h2>
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-8)",
            }}
          >
            {[
              {
                step: "01",
                title: "Upload a document",
                desc: "PDF, PNG, JPG, or TIFF. hamiGenZ accepts forms, notices, passports, letters — anything with text.",
              },
              {
                step: "02",
                title: "Ask a question",
                desc: "In English, Nepali, or Romanized Nepali. Ask what you need: “What is the deadline?” “How do I fill this?”",
              },
              {
                step: "03",
                title: "Get a clear answer",
                desc: "Structured explanation with what it means, what you need, and what to do next — with page references.",
              },
              {
                step: "04",
                title: "Check the evidence",
                desc: "Every claim shows where it came from. Verify for yourself, or ask follow-up questions.",
              },
            ].map((item, idx) => (
              <div
                key={item.step}
                style={{
                  display: "flex",
                  gap: "var(--space-6)",
                  alignItems: "flex-start",
                }}
              >
                <div
                  style={{
                    width: "48px",
                    flexShrink: 0,
                    fontFamily: "var(--font-mono)",
                    fontSize: "var(--text-lg)",
                    fontWeight: "var(--font-bold)",
                    color: "var(--color-accent)",
                    paddingTop: "var(--space-1)",
                  }}
                >
                  {item.step}
                </div>
                <div>
                  <h3
                    style={{
                      fontSize: "var(--text-lg)",
                      color: "var(--color-text-primary)",
                      fontWeight: "var(--font-semibold)",
                      marginBottom: "var(--space-2)",
                    }}
                  >
                    {item.title}
                  </h3>
                  <p
                    style={{
                      fontSize: "var(--text-sm)",
                      color: "var(--color-text-secondary)",
                      lineHeight: "1.5",
                    }}
                  >
                    {item.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────── */}
      <section
        id="final-cta-section"
        style={{
          padding: "var(--space-24) var(--space-6)",
          background: "var(--color-bg-alt)",
          textAlign: "center",
        }}
      >
        <div
          id="final-cta"
          style={{
            opacity: 0,
            transform: "translateY(20px) scale(0.97)",
            maxWidth: "600px",
            margin: "0 auto",
          }}
        >
          <p
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "var(--text-3xl)",
              color: "var(--color-text-primary)",
              marginBottom: "var(--space-6)",
              lineHeight: "1.3",
            }}
          >
            Complex information shouldn&apos;t be difficult to understand.
          </p>
          <div
            style={{
              display: "flex",
              gap: "var(--space-4)",
              justifyContent: "center",
              flexWrap: "wrap",
              marginBottom: "var(--space-8)",
            }}
          >
            <a
              href="#open-workspace"
              style={{
                background: "var(--color-accent)",
                color: "white",
                padding: "var(--space-4) var(--space-8)",
                borderRadius: "var(--radius-lg)",
                fontSize: "var(--text-lg)",
                fontWeight: "var(--font-semibold)",
                textDecoration: "none",
                transition: "background var(--duration-fast) var(--ease-default), transform var(--duration-fast) var(--ease-default)",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.background = "var(--color-accent-hover)";
                (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(-2px)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLAnchorElement).style.background = "var(--color-accent)";
                (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(0)";
              }}
            >
              Try hamiGenZ
            </a>
          </div>
          <p
            style={{
              color: "var(--color-text-tertiary)",
              fontSize: "var(--text-sm)",
            }}
          >
            Don&apos;t understand it? Ask hamiGenZ.
          </p>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────── */}
      <footer
        style={{
          padding: "var(--space-8) var(--space-6)",
          borderTop: "1px solid var(--color-border)",
          textAlign: "center",
          fontSize: "var(--text-sm)",
          color: "var(--color-text-tertiary)",
        }}
      >
        <div
          style={{
            maxWidth: "1200px",
            margin: "0 auto",
            display: "flex",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "var(--space-4)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-2)",
              fontWeight: "var(--font-bold)",
              color: "var(--color-text-primary)",
              fontSize: "var(--text-base)",
            }}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <rect width="20" height="20" rx="4" fill="#c8520b" />
              <path
                d="M6 7h8M6 10h8M6 13h5"
                stroke="white"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
            hamiGenZ
          </div>
          <div>
            Built for Nepal. Fully local. 100% free.
          </div>
        </div>
      </footer>
    </div>
  );
}
