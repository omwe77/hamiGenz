"use client";

import React, { useEffect, useRef } from "react";
import { drawTrail, isReducedMotion } from "@/lib/motion";

export interface EvidenceTrailProps {
  progress: number;
  className?: string;
  milestones?: { id: string; label: string; positionPercent: number }[];
}

export function EvidenceTrail({
  progress,
  className = "",
  milestones = [
    { id: "read", label: "Step 01", positionPercent: 16.66 },
    { id: "understand", label: "Step 02", positionPercent: 50.0 },
    { id: "verify", label: "Step 03", positionPercent: 83.33 },
  ],
}: EvidenceTrailProps) {
  const pathRef = useRef<SVGPathElement>(null);
  const totalLengthRef = useRef(0);

  useEffect(() => {
    const pathEl = pathRef.current;
    if (!pathEl) return;
    totalLengthRef.current = Math.max(0, pathEl.getTotalLength());
    if (isReducedMotion()) {
      pathEl.style.strokeDashoffset = "0";
      pathEl.style.strokeDasharray = "none";
    }
  }, []);

  useEffect(() => {
    if (pathRef.current && totalLengthRef.current > 0) {
      drawTrail(pathRef.current, progress, totalLengthRef.current);
    }
  }, [progress]);

  return (
    <div className={`evidence-trail-container ${className}`} aria-hidden="true">
      <svg
        className="evidence-trail-svg"
        viewBox="0 0 1200 64"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="evidenceTrailGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="var(--color-accent)" stopOpacity="0.85" />
            <stop offset="50%" stopColor="#d97706" stopOpacity="1" />
            <stop offset="100%" stopColor="#15803d" stopOpacity="0.9" />
          </linearGradient>
          <filter id="trailGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Ambient background guide line */}
        <path
          d="M 120 32 C 320 32, 460 32, 600 32 C 740 32, 880 32, 1080 32"
          stroke="var(--color-border)"
          strokeWidth="1.5"
          strokeDasharray="4 4"
          fill="none"
          opacity="0.6"
        />

        {/* The active progressive drawing stroke */}
        <path
          ref={pathRef}
          d="M 120 32 C 320 32, 460 32, 600 32 C 740 32, 880 32, 1080 32"
          stroke="url(#evidenceTrailGrad)"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          filter="url(#trailGlow)"
          vectorEffect="non-scaling-stroke"
        />
      </svg>

      {/* Dynamic milestone nodes */}
      {milestones.map((ms) => {
        const isActive = progress >= ms.positionPercent / 100 - 0.05;
        return (
          <div
            key={ms.id}
            className={`evidence-milestone-node ${isActive ? "is-active" : ""}`}
            style={{ left: `${ms.positionPercent}%`, top: "32px" }}
          >
            <span className="milestone-core" />
            <span className="milestone-halo" />
          </div>
        );
      })}

      <style jsx>{`
        .evidence-trail-container {
          position: absolute;
          top: -30px;
          left: 0;
          right: 0;
          height: 64px;
          pointer-events: none;
          z-index: 2;
        }
        .evidence-trail-svg {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
        }
        .evidence-milestone-node {
          position: absolute;
          transform: translate(-50%, -50%);
          width: 16px;
          height: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .milestone-core {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: var(--color-surface);
          border: 2px solid var(--color-border);
          transition: background 0.3s ease, border-color 0.3s ease, transform 0.3s ease;
          z-index: 1;
        }
        .milestone-halo {
          position: absolute;
          inset: -4px;
          border-radius: 50%;
          background: rgba(200, 82, 11, 0.15);
          opacity: 0;
          transform: scale(0.6);
          transition: opacity 0.3s ease, transform 0.3s ease;
        }
        .evidence-milestone-node.is-active .milestone-core {
          background: var(--color-accent);
          border-color: #ffffff;
          box-shadow: 0 0 8px rgba(200, 82, 11, 0.5);
          transform: scale(1.25);
        }
        .evidence-milestone-node.is-active .milestone-halo {
          opacity: 1;
          transform: scale(1);
          animation: pulseHalo 2s infinite ease-out;
        }
        @keyframes pulseHalo {
          0% { transform: scale(1); opacity: 0.6; }
          100% { transform: scale(1.8); opacity: 0; }
        }
        @media (max-width: 768px) {
          .evidence-trail-container {
            display: none !important;
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .evidence-milestone-node.is-active .milestone-halo {
            animation: none !important;
          }
          .milestone-core {
            transition: none !important;
          }
        }
      `}</style>
    </div>
  );
}
