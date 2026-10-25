"use client";

import { useRef, useEffect, useState, useCallback, type RefObject } from "react";
import { isReducedMotion } from "@/lib/motion";

interface ProvenanceThreadProps {
  containerRef: RefObject<HTMLElement | null>;
}

interface MilestonePoint {
  id: string;
  label: string;
  x: number;
  y: number;
  lengthRatio: number; // 0..1 along the path
}

export default function ProvenanceThread({ containerRef }: ProvenanceThreadProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const pathRef = useRef<SVGPathElement>(null);
  const ghostPathRef = useRef<SVGPathElement>(null);
  const beaconRef = useRef<SVGCircleElement>(null);
  const beaconHaloRef = useRef<SVGCircleElement>(null);

  const [pathData, setPathData] = useState<string>("");
  const [pathLength, setPathLength] = useState<number>(0);
  const [milestones, setMilestones] = useState<MilestonePoint[]>([]);
  const [isReady, setIsReady] = useState(false);

  // Compute smooth cubic Bezier spline connecting anchor elements across the entire page
  const updateSpline = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const containerRect = container.getBoundingClientRect();
    const cWidth = containerRect.width;
    const cHeight = container.scrollHeight;

    if (cWidth <= 0 || cHeight <= 0) return;

    const isMobile = cWidth < 768;

    // Narrative sequence of anchors spanning from Hero top down through Footer
    const anchorDefs = [
      { id: "prov-anchor-hero", label: "Evidence Grounding", verticalAlign: "top", yOffset: -4 },
      { id: "prov-anchor-sandbox", label: "Evidence Extraction", verticalAlign: "bottom", yOffset: 8 },
      { id: "prov-anchor-ledger", label: "Core Principles", verticalAlign: "top", yOffset: 12 },
      { id: "prov-anchor-read", label: "01 Read", verticalAlign: "top", yOffset: 24 },
      { id: "prov-anchor-understand", label: "02 Understand", verticalAlign: "top", yOffset: 24 },
      { id: "prov-anchor-verify", label: "03 Verify", verticalAlign: "top", yOffset: 24 },
      { id: "prov-anchor-work-1", label: "Select Notice", verticalAlign: "top", yOffset: 12 },
      { id: "prov-anchor-work-2", label: "Ask Query", verticalAlign: "top", yOffset: 12 },
      { id: "prov-anchor-work-3", label: "Audit Citation", verticalAlign: "top", yOffset: 12 },
      { id: "prov-anchor-cta", label: "Open Workspace", verticalAlign: "center", yOffset: 0 },
      { id: "prov-anchor-footer", label: "Civic Provenance", verticalAlign: "top", yOffset: 24 },
    ];

    const rawPoints: { id: string; label: string; x: number; y: number }[] = [];

    anchorDefs.forEach(({ id, label, verticalAlign, yOffset }) => {
      const el = document.getElementById(id);
      if (el) {
        const r = el.getBoundingClientRect();
        let x = r.left - containerRect.left + r.width / 2;
        let y = r.top - containerRect.top;

        if (verticalAlign === "center") {
          y += r.height / 2;
        } else if (verticalAlign === "bottom") {
          y += r.height;
        }
        y += yOffset;

        if (isMobile) {
          // On mobile, align cleanly in the left gutter (32px - 44px) along the step badges
          const stepOffset = rawPoints.length % 2 === 0 ? 0 : 6;
          x = Math.max(26, Math.min(46, 32 + stepOffset));
        } else {
          // On desktop, keep clamped safely inside viewport
          x = Math.max(48, Math.min(cWidth - 48, x));
        }

        rawPoints.push({ id, label, x, y });
      }
    });

    if (rawPoints.length < 2) return;

    // Build flowing cubic Bezier spline through the sequential narrative points
    let d = `M ${rawPoints[0].x.toFixed(1)} ${rawPoints[0].y.toFixed(1)}`;

    for (let i = 0; i < rawPoints.length - 1; i++) {
      const p0 = rawPoints[Math.max(0, i - 1)];
      const p1 = rawPoints[i];
      const p2 = rawPoints[i + 1];
      const p3 = rawPoints[Math.min(rawPoints.length - 1, i + 2)];

      const dy = p2.y - p1.y;
      const dx = p2.x - p1.x;

      if (isMobile) {
        // Vertical spine with subtle organic curvature
        const cp1x = p1.x + (dx * 0.12);
        const cp1y = p1.y + Math.max(16, dy * 0.4);
        const cp2x = p2.x - (dx * 0.12);
        const cp2y = p2.y - Math.max(16, dy * 0.4);
        d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
      } else {
        // Desktop: Generous fluid weaving S-curve
        let cp1x: number;
        let cp1y: number;
        let cp2x: number;
        let cp2y: number;

        if (Math.abs(dy) < 60) {
          // Horizontal transition between cards on same row: arch smoothly above
          const arc = Math.min(32, Math.abs(dx) * 0.15);
          cp1x = p1.x + dx * 0.35;
          cp1y = p1.y - arc;
          cp2x = p1.x + dx * 0.65;
          cp2y = p2.y - arc;
        } else {
          // Vertical descent between sections
          cp1x = p1.x + (p2.x - p0.x) * 0.15;
          cp1y = p1.y + dy * 0.42;
          cp2x = p2.x - (p3.x - p1.x) * 0.15;
          cp2y = p2.y - dy * 0.42;
        }

        d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
      }
    }

    setPathData(d);

    // Compute exact lengths for milestones
    requestAnimationFrame(() => {
      const pathEl = pathRef.current;
      if (pathEl) {
        const total = pathEl.getTotalLength();
        if (total > 0) {
          setPathLength(total);

          const calculatedMilestones: MilestonePoint[] = rawPoints.map((pt, idx) => ({
            id: pt.id,
            label: pt.label,
            x: pt.x,
            y: pt.y,
            lengthRatio: rawPoints.length > 1 ? idx / (rawPoints.length - 1) : 0,
          }));

          setMilestones(calculatedMilestones);
          setIsReady(true);
        }
      }
    });
  }, [containerRef]);

  // Recalculate on mount, resize, and DOM changes
  useEffect(() => {
    updateSpline();

    const handleResize = () => {
      updateSpline();
    };

    window.addEventListener("resize", handleResize, { passive: true });

    let resizeObserver: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined" && containerRef.current) {
      resizeObserver = new ResizeObserver(() => {
        updateSpline();
      });
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      window.removeEventListener("resize", handleResize);
      if (resizeObserver) resizeObserver.disconnect();
    };
  }, [updateSpline, containerRef]);

  // High-performance scroll loop driving strokeDashoffset and traveling beacon
  useEffect(() => {
    if (!isReady || !pathLength) return;

    const pathEl = pathRef.current;
    const ghostEl = ghostPathRef.current;
    const beaconEl = beaconRef.current;
    const haloEl = beaconHaloRef.current;
    const svgEl = svgRef.current;

    if (!pathEl || !svgEl) return;

    // Reduced motion handling
    if (isReducedMotion()) {
      pathEl.style.strokeDashoffset = "0";
      pathEl.style.strokeDasharray = "none";
      if (ghostEl) ghostEl.style.opacity = "0";
      if (beaconEl) beaconEl.style.opacity = "0";
      if (haloEl) haloEl.style.opacity = "0";

      const milestoneGroups = svgEl.querySelectorAll<SVGGElement>(".prov-milestone-group");
      milestoneGroups.forEach((g) => g.classList.add("is-active"));
      return;
    }

    pathEl.style.strokeDasharray = `${pathLength}`;

    let rafId = 0;

    const updateScrollProgress = () => {
      const scrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight;
      const vh = window.innerHeight || 800;
      const totalTravel = scrollHeight - vh;
      const currentScroll = window.scrollY || window.pageYOffset || 0;

      // Exactly 0 at scroll top, exactly 1 at scroll bottom
      const progress = totalTravel > 0 ? Math.min(1, Math.max(0, currentScroll / totalTravel)) : 0;

      const drawn = pathLength * progress;
      const offset = Math.max(0, pathLength - drawn);
      pathEl.style.strokeDashoffset = `${offset}px`;

      // Update traveling beacon at the leading edge
      if (drawn > 0 && beaconEl) {
        const pt = pathEl.getPointAtLength(drawn);
        beaconEl.setAttribute("cx", pt.x.toFixed(1));
        beaconEl.setAttribute("cy", pt.y.toFixed(1));
        beaconEl.style.opacity = progress > 0.005 ? "1" : "0";

        if (haloEl) {
          haloEl.setAttribute("cx", pt.x.toFixed(1));
          haloEl.setAttribute("cy", pt.y.toFixed(1));
          haloEl.style.opacity = progress > 0.005 ? "0.6" : "0";
        }
      } else if (beaconEl) {
        beaconEl.style.opacity = "0";
        if (haloEl) haloEl.style.opacity = "0";
      }

      // Activate milestone markers directly via DOM classList (no React re-renders while scrolling)
      const milestoneGroups = svgEl.querySelectorAll<SVGGElement>(".prov-milestone-group");
      milestoneGroups.forEach((g) => {
        const ratio = parseFloat(g.getAttribute("data-ratio") || "0");
        const isActive = progress >= ratio - 0.02;
        g.classList.toggle("is-active", isActive);
      });
    };

    const onScroll = () => {
      if (rafId) return;
      rafId = requestAnimationFrame(() => {
        updateScrollProgress();
        rafId = 0;
      });
    };

    // Initial paint for current scroll position
    updateScrollProgress();

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      window.removeEventListener("scroll", onScroll);
    };
  }, [isReady, pathLength]);

  if (!pathData) return null;

  return (
    <div
      className="provenance-thread-wrapper"
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        zIndex: 0,
        overflow: "visible",
      }}
      aria-hidden="true"
    >
      <svg
        ref={svgRef}
        style={{
          width: "100%",
          height: "100%",
          overflow: "visible",
          position: "absolute",
          top: 0,
          left: 0,
        }}
      >
        <defs>
          <linearGradient id="provenanceGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#c8520b" stopOpacity="0.45" />
            <stop offset="35%" stopColor="#c8520b" stopOpacity="0.95" />
            <stop offset="75%" stopColor="#ea580c" stopOpacity="1" />
            <stop offset="100%" stopColor="#f97316" stopOpacity="0.85" />
          </linearGradient>

          <filter id="provenanceGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <filter id="beaconGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="0" stdDeviation="5" floodColor="#c8520b" floodOpacity="0.85" />
          </filter>
        </defs>

        {/* 1. Ghost track */}
        <path
          ref={ghostPathRef}
          d={pathData}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth="2"
          strokeDasharray="6 6"
          opacity="0.28"
        />

        {/* 2. Progressively drawn active stroke */}
        <path
          ref={pathRef}
          d={pathData}
          fill="none"
          stroke="url(#provenanceGrad)"
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          filter="url(#provenanceGlow)"
          style={{
            transition: "stroke-dashoffset 0.06s linear",
          }}
        />

        {/* 3. Traveling beacon halo */}
        <circle
          ref={beaconHaloRef}
          r="13"
          fill="none"
          stroke="#c8520b"
          strokeWidth="1.5"
          opacity="0"
          style={{
            transition: "opacity 0.2s ease",
            transformOrigin: "center",
          }}
        />

        {/* 4. Traveling beacon core */}
        <circle
          ref={beaconRef}
          r="5.5"
          fill="#c8520b"
          stroke="#ffffff"
          strokeWidth="2"
          filter="url(#beaconGlow)"
          opacity="0"
          style={{
            transition: "opacity 0.2s ease",
          }}
        />

        {/* 5. Synchronized milestone nodes */}
        {milestones.map((m) => (
          <g
            key={m.id}
            id={`prov-milestone-${m.id}`}
            className="prov-milestone-group"
            data-ratio={m.lengthRatio.toFixed(4)}
          >
            <circle
              cx={m.x}
              cy={m.y}
              r="11"
              className="milestone-pulse-ring"
            />
            <circle
              cx={m.x}
              cy={m.y}
              r="4.5"
              className="milestone-core-dot"
            />
          </g>
        ))}
      </svg>
    </div>
  );
}
