/* The Wall — the background as a built surface rather than a blank one.
 *
 * Most of any page is background. Left inert it wastes the majority of the
 * canvas, so here it is composed of five layers, each drawn from the sourced
 * art research and each doing one job:
 *
 *   1 · aurora    three wells of pigment on mutually prime cycles; the field
 *                 retints per route so scroll position and section are legible
 *                 without a label  (kept from the existing AuroraField)
 *   2 · weave     the Athangudi rhombille floor, translating along exactly two
 *                 lattice periods so it reads as a floor being laid and never
 *                 visibly seams or jumps
 *   3 · circles   the Auroville amphitheatre's offset concentric family —
 *                 nested but eccentric, because Δc < ΔR. That single asymmetry
 *                 is what stops concentric circles reading as a target. Slow
 *                 rotation walks the narrow side of the band around the page.
 *   4 · discs     the Matrimandir disc field: two radii at ratio 1 : 1.53,
 *                 twice as many small as large, small convex and large concave
 *                 so their highlights travel in opposite directions. That
 *                 inversion is what makes the real dome shimmer.
 *   5 · grain     wide low-contrast gradients band badly on 8-bit displays.
 *
 * Everything animates on transform or opacity only, every loop returns to its
 * exact start, and all of it stops under prefers-reduced-motion. No layer
 * carries information, so losing the motion loses nothing but the motion.
 *
 * Geometry and opacity ceilings: art-reference-tn.md, art-reference-pondicherry.md
 */

import { useEffect, useRef } from "react";
import { RhombilleField } from "./Athangudi";

const REDUCED =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/* ------------------------------------------------------------------ *
 * Offset concentric circles.
 *
 *   r_i = R_inner + i·ΔR      ΔR = (R_outer − R_inner)/n
 *   c_i = (i·Δc, 0)           Δc constant, and Δc < ΔR
 *
 * Real amphitheatre figures: R_inner 37.5 m, R_outer 49 m, n = 7.
 * ------------------------------------------------------------------ */
function Concentrics() {
  const R_IN = 37.5;
  const R_OUT = 49;
  const N = 7;
  const dR = (R_OUT - R_IN) / N;
  const dC = dR * 0.55; // strictly less than dR — nested but eccentric

  const rings = Array.from({ length: N + 1 }, (_, i) => (
    <circle key={i} cx={(i * dC).toFixed(3)} cy="0" r={(R_IN + i * dR).toFixed(3)} />
  ));

  return (
    <svg className="wl-circles" viewBox="-60 -60 120 120" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeWidth="0.35">
        {rings}
      </g>
    </svg>
  );
}

export default function Wall() {
  const ref = useRef<HTMLDivElement>(null);

  /* Pointer light. Written straight to custom properties on the element, so
     moving the mouse never triggers a React render. Skipped entirely on
     coarse pointers and under reduced motion. */
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

    const onMove = (e: PointerEvent) => {
      tx = (e.clientX / window.innerWidth) * 100;
      ty = (e.clientY / window.innerHeight) * 100;
      if (!raf) raf = requestAnimationFrame(tick);
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div className="wall" ref={ref} aria-hidden="true">
      <div className="wl-well wl-a" />
      <div className="wl-well wl-b" />
      <div className="wl-well wl-c" />

      <div className="wl-weave">
        <RhombilleField s={26} className="wl-weave-in" />
      </div>

      <div className="wl-circlewrap">
        <Concentrics />
      </div>

      <div className="wl-discs" />
      <div className="wl-light" />
      <div className="wl-grain" />
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Tone + progress hooks
 * ------------------------------------------------------------------ */

/**
 * Retints the wall as sections pass the middle of the viewport.
 *
 * Deliberately not an IntersectionObserver with ratio thresholds: a section
 * taller than the (margin-shrunk) root can never reach a high ratio, so the
 * tone would simply never change. Whichever section owns the viewport's centre
 * line wins — unambiguous at any section height.
 */
export function useWallTone() {
  useEffect(() => {
    const sections = [...document.querySelectorAll<HTMLElement>("[data-tone]")];
    if (!sections.length) return;

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
 * Scroll progress through an element, 0 → 1, written as a CSS variable.
 *
 * Written synchronously on scroll rather than deferred to rAF: one rect read
 * plus one custom-property write is cheap, and rAF does not fire in a tab that
 * is not painting — which would strand progress at 0 and leave the transform
 * it drives at its start state. A frame loop may make something smoother; it
 * must never be the only thing that makes it correct.
 */
export function useScrollProgress(
  ref: React.RefObject<HTMLElement>,
  varName = "--p",
) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;

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
