/* The overture — a photographic camera push that lands on the home page.
 *
 * Earlier versions drew this in CSS gradients and SVG. That was the mistake:
 * the reference's richness is PHOTOGRAPHIC, and no gradient reproduces a real
 * sunset or a real cloud deck. These are free-licence photographs (Unsplash
 * Licence — commercial use, no attribution required), cropped so no third-party
 * branding ships, and graded in CSS to the reference's palette.
 *
 * Layers, furthest first — each moves at its own rate, which is what makes it
 * read as depth rather than as one image being zoomed:
 *   0  sky    the sunset field, barely moves
 *   1  sun    bloom, swells as the camera enters the light
 *   2  deck   the cloud floor, rises as the camera descends toward it
 *   3  bank   a near cloud bank, drops away and blurs as it passes
 *
 * Everything is driven by one number, `--p` (0 → 1), written SYNCHRONOUSLY on
 * scroll. Never rAF: it does not fire in a tab that is not painting, which
 * would freeze the whole approach on its first frame.
 */

import { useEffect, useRef, useState, type CSSProperties } from "react";

const REDUCED =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export default function Overture({
  screens = 2.4,
  word = "வணிகம்",
}: {
  screens?: number;
  word?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  // Held until the sky has decoded. Without it the first paint is a black
  // rectangle that then pops — worse than a beat of nothing.
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const img = new Image();
    img.onload = () => setReady(true);
    img.onerror = () => setReady(true); // never trap the page behind an asset
    img.src = "/scene/sky.jpg";
    // and never wait longer than a beat, whatever the network does
    const t = setTimeout(() => setReady(true), 2500);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (REDUCED) return;
    const el = ref.current;
    if (!el) return;
    const update = () => {
      const r = el.getBoundingClientRect();
      const span = r.height - window.innerHeight;
      const p = span > 0 ? -r.top / span : 0;
      el.style.setProperty("--p", Math.min(1, Math.max(0, p)).toFixed(5));
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [screens]);

  const stage = (
    <div className="ov-stage">
      <div className="ov-l ov-sky" />
      <div className="ov-l ov-sun" />
      <div className="ov-l ov-deck" />
      <div className="ov-l ov-bank" />
      <div className="ov-grade" />
      <div className="ov-vig" />
    </div>
  );

  if (REDUCED) {
    return (
      <div className="ov ov-still" data-ready="1">
        <div className="ov-pin">
          {stage}
          <div className="ov-word">{word}</div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="ov"
      ref={ref}
      data-ready={ready ? "1" : undefined}
      style={{ height: `${screens * 100}vh` } as CSSProperties}
      aria-hidden="true"
    >
      <div className="ov-pin">
        {stage}
        <div className="ov-word">{word}</div>
        <div className="ov-out" />
      </div>
    </div>
  );
}
