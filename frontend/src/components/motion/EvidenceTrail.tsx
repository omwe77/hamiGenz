"use client";

import { useRef, useEffect, useState } from "react";

interface Milestone {
  id: string;
  label: string;
  pct: number; // 0-100 along the trail
}

const MILESTONES: Milestone[] = [
  { id: "read",       label: "Read",       pct: 10 },
  { id: "understand", label: "Understand", pct: 50 },
  { id: "verify",     label: "Verify",     pct: 90 },
];

interface EvidenceTrailProps {
  /** 0-1 scroll progress for the section containing the trail */
  progress: number;
}

export default function EvidenceTrail({ progress }: EvidenceTrailProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [pathLength, setPathLength] = useState(0);

  // Measure path length after mount
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const path = svg.querySelector("path");
    if (path) setPathLength(path.getTotalLength());
  }, []);

  const drawn = pathLength * Math.min(1, Math.max(0, progress));
  const dashOffset = pathLength - drawn;

  const activeMilestones = MILESTONES.filter((m) => (m.pct / 100) <= progress);

  return (
    <div className="evidence-trail-container" aria-hidden="true">
      <svg ref={svgRef} className="evidence-trail-svg" preserveAspectRatio="none">
        {/* Ghost track */}
        <path
          d="M 5% 50% C 20% 20%, 40% 80%, 50% 50% S 80% 20%, 95% 50%"
          fill="none"
          stroke="var(--color-border)"
          strokeWidth="1.5"
          strokeDasharray="4 4"
        />
        {/* Animated fill */}
        <path
          d="M 5% 50% C 20% 20%, 40% 80%, 50% 50% S 80% 20%, 95% 50%"
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray={pathLength}
          strokeDashoffset={dashOffset}
          style={{ transition: "stroke-dashoffset 0.08s linear" }}
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
          </div>
        );
      })}
    </div>
  );
}
