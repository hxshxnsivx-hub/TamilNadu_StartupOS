/* AuroraField — the background doing real work.
 *
 * Most of a landing page is background. Left inert it wastes the majority of
 * the canvas, so here it carries the palette itself:
 *
 *   · three wells of pigment drifting on long, mutually prime cycles, so the
 *     field never visibly loops
 *   · the hue set retints per section as you scroll (--aurora-1/2/3), which
 *     makes scroll position legible without a single label
 *   · a pointer-tracked light, so the surface answers the cursor
 *   · grain over the top, because wide low-contrast gradients band badly on
 *     8-bit displays
 *
 * Pigments are the project's own: bottle green, lac red (arakku), brass,
 * young-mango-leaf. Everything is transform/opacity only, and the pointer
 * light is skipped entirely on coarse pointers and under reduced motion.
 */

import { useEffect, useRef } from "react";

const REDUCED =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export default function AuroraField() {
  const ref = useRef<HTMLDivElement>(null);

  // Pointer light. Written straight to CSS custom properties on the element —
  // no React state, so moving the mouse never triggers a render.
  useEffect(() => {
    if (REDUCED) return;
    if (!window.matchMedia("(pointer: fine)").matches) return;
    const el = ref.current;
    if (!el) return;

    let raf = 0;
    let tx = 50;
    let ty = 40;
    let cx = 50;
    let cy = 40;

    const onMove = (e: PointerEvent) => {
      tx = (e.clientX / window.innerWidth) * 100;
      ty = (e.clientY / window.innerHeight) * 100;
      if (!raf) raf = requestAnimationFrame(tick);
    };

    // ease toward the pointer so the light trails rather than snaps
    const tick = () => {
      cx += (tx - cx) * 0.06;
      cy += (ty - cy) * 0.06;
      el.style.setProperty("--px", `${cx.toFixed(2)}%`);
      el.style.setProperty("--py", `${cy.toFixed(2)}%`);
      raf =
        Math.abs(tx - cx) > 0.1 || Math.abs(ty - cy) > 0.1
          ? requestAnimationFrame(tick)
          : 0;
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div className="aurora" ref={ref} aria-hidden="true">
      <div className="aurora-well aurora-a" />
      <div className="aurora-well aurora-b" />
      <div className="aurora-well aurora-c" />
      <div className="aurora-light" />
      <div className="aurora-grain" />
    </div>
  );
}

/**
 * Retints the aurora as sections pass the midpoint of the viewport.
 *
 * Each element carrying data-tone hands its palette to the field while it
 * owns the screen, so the background becomes a readout of where you are.
 */
export function useAuroraTone() {
  useEffect(() => {
    const sections = [...document.querySelectorAll<HTMLElement>("[data-tone]")];
    if (!sections.length) return;

    // Deliberately NOT an IntersectionObserver with ratio thresholds: a section
    // taller than the (margin-shrunk) root can never reach a high ratio, so the
    // tone would simply never change. Whichever section owns the viewport's
    // centre line wins — unambiguous at any section height.
    const pick = () => {
      const mid = window.innerHeight / 2;
      let chosen = sections[0];
      for (const s of sections) {
        const r = s.getBoundingClientRect();
        if (r.top <= mid && r.bottom >= mid) {
          chosen = s;
          break;
        }
        if (r.top > mid) break;
        chosen = s;
      }
      const tone = chosen.dataset.tone || "base";
      if (document.documentElement.getAttribute("data-aurora") !== tone) {
        document.documentElement.setAttribute("data-aurora", tone);
      }
    };

    pick();
    window.addEventListener("scroll", pick, { passive: true });
    window.addEventListener("resize", pick);
    return () => {
      window.removeEventListener("scroll", pick);
      window.removeEventListener("resize", pick);
      document.documentElement.removeAttribute("data-aurora");
    };
  }, []);
}

/**
 * Scroll progress through a given element, 0 → 1, as a CSS variable.
 * Drives progress-linked transforms rather than one-shot reveals.
 */
export function useScrollProgress(
  ref: React.RefObject<HTMLElement>,
  varName = "--p",
) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // Written synchronously on scroll rather than deferred to rAF. One rect
    // read plus one custom-property write is cheap, and rAF does not fire in a
    // tab that isn't painting — which would strand progress at 0 and leave the
    // rule undrawn. Correctness first; this is well inside budget.
    const update = () => {
      const r = el.getBoundingClientRect();
      const total = r.height + window.innerHeight;
      const p = total > 0 ? (window.innerHeight - r.top) / total : 0;
      el.style.setProperty(varName, Math.min(1, Math.max(0, p)).toFixed(4));
    };

    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [ref, varName]);
}
