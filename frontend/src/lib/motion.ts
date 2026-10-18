// ── hamiGenZ Motion & Scroll Engine ─────────────────────────────────────
// High-performance, accessible motion engine built for civic document UX.
// Zero runtime animation framework overhead; leverages native rAF, CSS variables,
// SVG stroke-dash calculations, and IntersectionObserver.
// Fully compliant with React 19 compiler rules and prefers-reduced-motion.
// ────────────────────────────────────────────────────────────────────────

import { useEffect, useState, type RefObject } from "react";

/**
 * Returns true if the user prefers reduced motion.
 * Safe for Server-Side Rendering (SSR).
 */
export function isReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export interface SectionProgressOptions {
  offsetStart?: number; // Viewport fraction when progress begins (default 0.9 = near bottom)
  offsetEnd?: number;   // Viewport fraction when progress completes (default 0.2 = near top)
}

/**
 * Calculates normalized scroll progress (0..1) through a section.
 * Complies with React 19 compiler rules by taking a RefObject and reading .current
 * only inside useEffect / rAF.
 */
export function useSectionScrollProgress(
  ref: RefObject<HTMLElement | null>,
  options: SectionProgressOptions = {}
): number {
  const { offsetStart = 0.9, offsetEnd = 0.2 } = options;
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
      const startY = windowHeight * offsetStart;
      const endY = windowHeight * offsetEnd;
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
  }, [ref, offsetStart, offsetEnd]);

  return progress;
}

/**
 * Tracks the global page scroll progress (0..1) from top to bottom.
 */
export function useGlobalScrollProgress(): number {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (isReducedMotion()) return;

    let rafId = 0;
    const update = () => {
      const totalScroll = document.documentElement.scrollHeight - window.innerHeight;
      const current = window.scrollY;
      const p = totalScroll > 0 ? Math.min(1, Math.max(0, current / totalScroll)) : 0;
      setProgress(p);
      rafId = 0;
    };

    const schedule = () => {
      if (rafId) return;
      rafId = requestAnimationFrame(update);
    };

    schedule();

    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule, { passive: true });

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, []);

  return progress;
}

/**
 * Calculates a smooth subtle parallax offset (pixels) based on distance from viewport center.
 * Does not trigger re-layouts when applied via transform: translate3d.
 */
export function useParallaxOffset(
  ref: RefObject<HTMLElement | null>,
  speed = 0.15
): number {
  const [offsetY, setOffsetY] = useState(0);

  useEffect(() => {
    if (typeof window === "undefined" || isReducedMotion()) return;

    const el = ref.current;
    if (!el) return;

    let rafId = 0;
    const update = () => {
      const rect = el.getBoundingClientRect();
      const viewportCenter = window.innerHeight / 2;
      const elCenter = rect.top + rect.height / 2;
      const diff = elCenter - viewportCenter;
      setOffsetY(Math.round(-diff * speed));
      rafId = 0;
    };

    const schedule = () => {
      if (rafId) return;
      rafId = requestAnimationFrame(update);
    };

    schedule();

    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule, { passive: true });

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, [ref, speed]);

  return offsetY;
}

/**
 * Drives an SVG path stroke so it draws progressively with `progress` (0..1).
 * Under reduced motion, the stroke is rendered fully drawn.
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

export interface RevealOptions {
  rootMargin?: string;
  threshold?: number;
  staggerDelayMs?: number;
}

/**
 * Observes elements matching `selector` and adds `visible` class as they enter the viewport.
 * Automatically cleans up observer on unmount.
 */
export function useEntranceReveals(
  selector: string,
  options: RevealOptions = {}
): void {
  const { rootMargin = "0px 0px -8% 0px", threshold = 0.1, staggerDelayMs = 60 } = options;

  useEffect(() => {
    if (typeof window === "undefined") return;
    const elements = document.querySelectorAll<HTMLElement>(selector);
    if (!elements.length) return;

    if (isReducedMotion() || !("IntersectionObserver" in window)) {
      elements.forEach((el) => el.classList.add("visible"));
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

    elements.forEach((el) => observer.observe(el));

    return () => {
      observer.disconnect();
    };
  }, [selector, rootMargin, threshold, staggerDelayMs]);
}
