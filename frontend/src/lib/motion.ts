// ── hamiGenZ Motion Utilities ──────────────────────────────────────────
// Lightweight, accessible motion utilities built for civic document UX.
// Zero external dependencies beyond existing standard browser APIs.
// Respects prefers-reduced-motion, supports React Strict Mode, and prevents memory leaks.
// ──────────────────────────────────────────────────────────────────────

import { useEffect, useState, type RefObject } from "react";

// ── Reduced Motion Detection ───────────────────────────────────────────

/**
 * Returns true if the user has requested reduced motion.
 * Safe for Server-Side Rendering (SSR).
 */
export function isReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

// ── Section Scroll Progress ────────────────────────────────────────────

/**
 * Calculates normalized scroll progress (0..1) through a container element.
 * Accepts a React RefObject to comply with React 19 ref access rules.
 */
export function useSectionScrollProgress(ref: RefObject<HTMLElement | null>): number {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (typeof window === "undefined") return;

    if (isReducedMotion()) {
      const id = requestAnimationFrame(() => setProgress(1));
      return () => cancelAnimationFrame(id);
    }

    const sectionEl = ref.current;
    if (!sectionEl) return;

    const calc = () => {
      const rect = sectionEl.getBoundingClientRect();
      const windowHeight = window.innerHeight || 1;
      const startY = windowHeight * 0.9;
      const endY = windowHeight * 0.2;
      const currentY = rect.top;
      const p = (startY - currentY) / (startY - endY);
      return Math.min(1, Math.max(0, p));
    };

    let rafId = 0;
    const handleScroll = () => {
      if (rafId) return;
      rafId = requestAnimationFrame(() => {
        setProgress(calc());
        rafId = 0;
      });
    };

    handleScroll();

    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("resize", handleScroll, { passive: true });

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("resize", handleScroll);
    };
  }, [ref]);

  return progress;
}

// ── Scroll-Linked SVG Stroke Drawing (Evidence Trail) ──────────────────

/**
 * Drives an SVG path stroke so it draws progressively with `progress` (0..1).
 * Under reduced motion, the path is painted completely (static).
 */
export function drawTrail(
  pathEl: SVGPathElement | null,
  progress: number,
  totalLength: number
): void {
  if (!pathEl) return;
  if (isReducedMotion()) {
    pathEl.style.strokeDashoffset = "0";
    pathEl.style.strokeDasharray = "none";
    return;
  }
  const clamped = Math.min(1, Math.max(0, progress));
  const offset = (1 - clamped) * totalLength;
  pathEl.style.strokeDasharray = `${totalLength}`;
  pathEl.style.strokeDashoffset = `${offset}`;
}

// ── Entrance Reveals via IntersectionObserver ──────────────────────────

export interface RevealOptions {
  rootMargin?: string;
  threshold?: number;
  staggerDelayMs?: number;
}

/**
 * Observes elements matching `selector` and adds `visible` class once they enter viewport.
 * Safe for React Strict Mode and cleans up observer on unmount.
 */
export function useEntranceReveals(
  selector: string,
  { rootMargin = "0px 0px -8% 0px", threshold = 0.1, staggerDelayMs = 60 }: RevealOptions = {}
): void {
  useEffect(() => {
    if (typeof window === "undefined") return;
    const els = document.querySelectorAll<HTMLElement>(selector);
    if (!els.length) return;

    // Reduced motion or missing IntersectionObserver fallback
    if (isReducedMotion() || !("IntersectionObserver" in window)) {
      els.forEach((el) => el.classList.add("visible"));
      return;
    }

    let index = 0;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const target = entry.target as HTMLElement;
            if (staggerDelayMs > 0) {
              const delay = (index % 4) * staggerDelayMs;
              target.style.transitionDelay = `${delay}ms`;
              index++;
            }
            target.classList.add("visible");
            observer.unobserve(target);
          }
        });
      },
      { rootMargin, threshold }
    );

    els.forEach((el) => observer.observe(el));

    return () => {
      observer.disconnect();
    };
  }, [selector, rootMargin, threshold, staggerDelayMs]);
}

// ── Stagger Helper ─────────────────────────────────────────────────────

export function staggeredDelay(index: number, total: number, baseMs = 70): number {
  if (isReducedMotion()) return 0;
  return Math.min(baseMs * index, 280);
}
