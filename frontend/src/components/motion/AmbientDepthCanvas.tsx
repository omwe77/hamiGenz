"use client";

import React, { useRef } from "react";
import { useParallaxOffset, isReducedMotion } from "@/lib/motion";

export function AmbientDepthCanvas() {
  const canvasRef = useRef<HTMLDivElement>(null);
  const orb1Offset = useParallaxOffset(canvasRef, 0.08);
  const orb2Offset = useParallaxOffset(canvasRef, -0.06);

  const reduced = isReducedMotion();

  return (
    <div ref={canvasRef} className="ambient-depth-canvas" aria-hidden="true">
      {/* Precision architectural micro-grid */}
      <div className="ambient-grid-pattern" />

      {/* Warm terracotta ambient glow orb */}
      <div
        className="ambient-glow-orb orb-terracotta"
        style={{
          top: "12%",
          left: "15%",
          width: "360px",
          height: "360px",
          background: "radial-gradient(circle, rgba(200, 82, 11, 0.09) 0%, rgba(200, 82, 11, 0) 70%)",
          transform: reduced ? "none" : `translate3d(0, ${orb1Offset}px, 0)`,
        }}
      />

      {/* Gentle amber secondary glow orb */}
      <div
        className="ambient-glow-orb orb-amber"
        style={{
          top: "35%",
          right: "12%",
          width: "420px",
          height: "420px",
          background: "radial-gradient(circle, rgba(217, 119, 6, 0.07) 0%, rgba(217, 119, 6, 0) 70%)",
          transform: reduced ? "none" : `translate3d(0, ${orb2Offset}px, 0)`,
        }}
      />

      {/* Subtle emerald grounded aura near capabilities */}
      <div
        className="ambient-glow-orb orb-emerald"
        style={{
          top: "65%",
          left: "25%",
          width: "500px",
          height: "500px",
          background: "radial-gradient(circle, rgba(21, 128, 61, 0.05) 0%, rgba(21, 128, 61, 0) 75%)",
          transform: reduced ? "none" : `translate3d(0, ${Math.round(orb1Offset * 0.7)}px, 0)`,
        }}
      />
    </div>
  );
}
