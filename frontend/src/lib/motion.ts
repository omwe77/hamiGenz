// ──────────────────────────────────────────────────────────────────────
// motion.ts — hamiGenZ scroll-animation primitives
// --------------------------------────────────────────────────────────
// Reuses the EXISTING Anime.js dependency for the scroll-linked SVG trail
// and IntersectionObserver for entrance reveals. Native browser scroll,
// transform/opacity only, prefers-reduced-motion honoured, Strict Mode +
// Next.js client navigation safe.
//
// Not a use-case for a new animation package: no Framer Motion / Lenis /
// GSAP. All modules below are one or two small, independently testable
// functions so each can be verified in isolation.
// ──────────────────────────────────────────────────────────────────────

import * as anime from "animejs";
import { useEffect, useRef, useCallback, useState } from "react";

// ── Reduced motion detection ────────────────────────────────────────────

let reducedMotion = false;
let reducedMotionQuery: MediaQueryList | null = null;

export function initReducedMotion(): void {
  reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  reducedMotion = reducedMotionQuery.matches;
}

export function getReducedMotion(): boolean {
  if (reducedMotionQuery) return reducedMotionQuery.matches;
  return reducedMotion;
}

export function isReducedMotion(): boolean {
  return getReducedMotion();
}

// ── Section scroll progress (single source of truth for the trail) ─────

/**
 * Returns a 0..1 value describing how far the user has scrolled through
 * `sectionEl`. A section is "at 1.0" when its bottom edge has reached the
 * bottom of the viewport (i.e. the whole section is visible). A progress of
 * ~0.35 marks the moment the section's top is at the top of the viewport.
 *
 * The returned value is the latest read; it is stable between ticks. Consumers
 * drive a single rAF loop and read the latest snapshot.
 */
export function useSectionScrollProgress(sectionEl: HTMLElement | null): number {
  const [progress, setProgress] = useState(0);
  const tickRef = useRef<(() => void) | null>(null);
  const rafRef = useRef(0);

  const tick = useCallback(() => {
    if (!sectionEl) {
      setProgress(0);
      return;
    }
    const rect = sectionEl.getBoundingClientRect();
    const top = rect.top + window.scrollY;
    const bottom = top + rect.height;
    const visible = Math.max(
      0,
      Math.min(window.innerHeight, bottom) - Math.max(0, top)
    );
    const total = Math.max(0, bottom - top);
    const p = total === 0
      ? 0
      : Math.min(1, Math.max(0, (visible - window.innerHeight * 0.35) / total));
    setProgress(p);
  }, [sectionEl]);

  useEffect(() => {
    if (!sectionEl) return;
    let mounted = true;

    const schedule = () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        tick();
        rafRef.current = 0;
      });
    };

    // First tick immediately so the trail can draw on mount.
    tick();

    const onScroll = () => schedule();
    const onResize = () => schedule();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onResize);
    return () => {
      mounted = false;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onResize);
    };
  }, [sectionEl, tick]);

  return progress;
}

// ── Scroll-linked SVG stroke drawing (the evidence trail) ──────────────

/**
 * Drive an SVG path's stroke so it draws progressively with `progress`
 * (0..1). `totalLength` must equal `path.getTotalLength()` measured once.
 *
 * Under reduced motion the path is painted fully (static) — the content is
 * preserved and no motion is applied.
 */
export function drawTrail(
  pathEl: SVGPathElement | null,
  progress: number,
  totalLength: number
): void {
  if (!pathEl) return;
  if (isReducedMotion()) {
    // Static: paint the whole stroke, no animation.
    pathEl.style.strokeDashoffset = "0";
    pathEl.style.strokeDasharray = String(totalLength);
    return;
  }
  const offset = (1 - Math.min(1, Math.max(0, progress))) * totalLength;
  pathEl.style.strokeDashoffset = String(offset);
  pathEl.style.strokeDasharray = String(totalLength);
}

// ── Entrance reveals via IntersectionObserver (lightweight, staggered) ─

export interface RevealOptions {
  rootMargin?: string;
  threshold?: number;
  /** Play every item in `els` with this delay between each. */
  staggerDelayMs?: number;
}

/**
 * Observe every element matching `selector` and add `visible` once it enters
 * the viewport. `visible` is the CSS class that toggles opacity + translateY.
 * The observer is a single instance, so large document changes are cheap and
 * there are no per-item observers to leak.
 *
 * Safe under React Strict Mode: the effect cleans up on unmount/remount, and
 * elements that already matched keep their `visible` class (no replay).
 */
export function useEntranceReveals(
  selector: string,
  { rootMargin = "0px 0px -4% 0px", threshold = 0.1 }: RevealOptions = {}
): void {
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    const els = document.querySelectorAll<HTMLElement>(selector);

    // Safety fallback: if IntersectionObserver is unavailable, mark every
    // matched element visible so content is never hidden from a non-JS user.
    if (!("IntersectionObserver" in window)) {
      els.forEach((el) => el.classList.add("visible"));
      return;
    }

    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observerRef.current?.unobserve(entry.target);
          }
        });
      },
      { rootMargin, threshold }
    );
    els.forEach((el) => observerRef.current?.observe(el));
    return () => {
      observerRef.current?.disconnect();
      observerRef.current = null;
    };
  }, [selector, rootMargin, threshold]);
}

// ── Optional global thin scroll-progress indicator ─────────────────────

export interface ProgressBarEl {
  el: HTMLDivElement;
  maxScroll?: number;
}

/**
 * Set the scaleX of a thin progress bar to match `window.scrollY`. Uses a
 * single rAF loop. Under reduced motion the bar is hidden by the caller.
 */
export function useGlobalProgress({ el, maxScroll }: ProgressBarEl): void {
  useEffect(() => {
    if (isReducedMotion()) return;
    let raf = 0;

    const tick = () => {
      const scrollHeight =
        document.documentElement.scrollHeight - window.innerHeight;
      const p = scrollHeight > 0 ? Math.min(1, window.scrollY / scrollHeight) : 0;
      // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
      const rect = el.getBoundingClientRect();
      const width = el.clientWidth || 2;
      el.style.width = `${width}px`;
      el.style.transform = `scaleX(${p})`;
      el.style.webkitTransform = `scaleX(${p})`;
      raf = 0;
    };

    const schedule = () => {
      if (raf) cancelAnimationFrame(raf);
      raf = requestAnimationFrame(tick);
    };

    tick();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      if (raf) cancelAnimationFrame(raf);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, [el, maxScroll]);
}

// ── Demo-mode sample stagger (homepage) ────────────────────────────────

/**
 * Return a staggered delay (ms) for a list of items, keyed off mount index.
 * Zero for reduced motion so no animation runs.
 */
export function staggeredDelay(index: number, total: number, baseMs = 80): number {
  if (isReducedMotion()) return 0;
  // Even spacing across the group, so the last item isn't postponed far off
  // the screen; each item still gets a visible but short offset.
  const padded = Math.max(total, 1);
  return Math.min(baseMs * index, 320);
}
