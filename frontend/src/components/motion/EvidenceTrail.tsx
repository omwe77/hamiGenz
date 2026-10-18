"use client";

import { useRef, useEffect, useState } from "react";

interface Milestone {
  id: string;
  label: string;
  pct: number; // percentage along the trail (matches card centers: 16.67%, 50%, 83.33%)
}

const MILESTONES: Milestone[] = [
  { id: "read",       label: "01 Read",       pct: 16.67 },
  { id: "understand", label: "02 Understand", pct: 50.0 },
  { id: "verify",     label: "03 Verify",     pct: 83.33 },
];

interface EvidenceTrailProps {
  /** 0-1 scroll progress through the capabilities section */
  progress: number;
}

export default function EvidenceTrail({ progress }: EvidenceTrailProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const pathRef = useRef<SVGPathElement>(null);
  const [pathLength, setPathLength] = useState(1000);

  // Measure SVG path length accurately after mount
  useEffect(() => {
    if (pathRef.current) {
      const len = pathRef.current.getTotalLength();
      if (len > 0) setPathLength(len);
    }
  }, []);

  const clampedProgress = Math.min(1, Math.max(0, progress));
  const drawn = pathLength * clampedProgress;
  const dashOffset = Math.max(0, pathLength - drawn);

  const activeMilestones = MILESTONES.filter((m) => (m.pct / 100) <= clampedProgress + 0.05);

  return (
    <div className="evidence-trail-container" aria-hidden="true">
      <svg
        ref={svgRef}
        viewBox="0 0 1000 64"
        className="evidence-trail-svg"
        preserveAspectRatio="none"
        style={{ overflow: "visible" }}
      >
        <defs>
          <linearGradient id="evidenceTrailGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#c8520b" stopOpacity="0.4" />
            <stop offset="50%" stopColor="#c8520b" stopOpacity="1" />
            <stop offset="100%" stopColor="#ea580c" stopOpacity="1" />
          </linearGradient>
          <filter id="evidenceGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#c8520b" floodOpacity="0.45" />
          </filter>
        </defs>

        {/* Ghost track */}
        <path
          d="M 60 32 C 110 32, 130 32, 167 32 C 280 10, 380 54, 500 32 C 620 10, 720 54, 833 32 C 870 32, 910 32, 940 32"
          fill="none"
          stroke="var(--color-border)"
          strokeWidth="2"
          strokeDasharray="6 6"
          vectorEffect="non-scaling-stroke"
        />

        {/* Animated fill stroke */}
        <path
          ref={pathRef}
          d="M 60 32 C 110 32, 130 32, 167 32 C 280 10, 380 54, 500 32 C 620 10, 720 54, 833 32 C 870 32, 910 32, 940 32"
          fill="none"
          stroke="url(#evidenceTrailGrad)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={pathLength}
          strokeDashoffset={dashOffset}
          filter="url(#evidenceGlow)"
          vectorEffect="non-scaling-stroke"
          style={{ transition: "stroke-dashoffset 0.12s ease-out" }}
        />
      </svg>

      {MILESTONES.map((m) => {
        const isActive = activeMilestones.includes(m);
        return (
          <div
            key={m.id}
            className={`evidence-milestone-node${isActive ? " is-active" : ""}`}
            style={{ left: `${m.pct}%`, top: "50%" }}
            title={m.label}
          >
            <span className="milestone-halo" />
            <span className="milestone-core" />
            <span
              style={{
                position: "absolute",
                top: "-22px",
                fontSize: "10px",
                fontFamily: "var(--font-mono)",
                fontWeight: 600,
                letterSpacing: "0.04em",
                textTransform: "uppercase",
                whiteSpace: "nowrap",
                color: isActive ? "var(--color-accent)" : "var(--color-text-tertiary)",
                transition: "color 0.3s ease",
              }}
            >
              {m.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
