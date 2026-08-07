/* Zoom story — a camera flying through landscapes.
 *
 * The reference clip opens on a continuous push: clouds, then past a tower,
 * then into the sun, then it arrives at content. It is one camera move, not a
 * sequence of cuts, and scrolling back reverses it exactly.
 *
 * The whole effect is one number. For a scene at index i and overall progress
 * p across N scenes:
 *
 *     local = p·N − i          −1 = far ahead · 0 = at the camera · +1 = passed
 *     scale = 2^local          doubling per step, so the push feels constant
 *
 * An exponential scale is what makes this read as *travel* rather than as
 * something being resized: each scene grows by the same factor per unit of
 * scroll, exactly as real perspective behaves when you move at constant speed.
 * A linear scale looks like a zoom tool; 2^local looks like flight.
 *
 * Scenes fade in over local −1 → −0.55 and out over +0.55 → +1, so only ever
 * two are visible and the handover happens while both are mid-flight.
 *
 * `--z` is written SYNCHRONOUSLY on scroll. Never rAF: it does not fire in a
 * tab that is not painting, which would freeze every scene at its first frame.
 */

import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";

const REDUCED =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export type ZoomScene = {
  id: string;
  /** chapter number, e.g. "01" */
  n: string;
  place: string;
  placeTa?: string;
  title: string;
  lede?: string;
  meta?: string;
  layers: ReactNode;
};

export default function ZoomStory({
  scenes,
  screensPerScene = 1.6,
}: {
  scenes: ZoomScene[];
  /** scroll cost per scene, in viewports */
  screensPerScene?: number;
}) {
  const ref = useRef<HTMLElement>(null);
  const N = scenes.length;

  useEffect(() => {
    if (REDUCED) return;
    const el = ref.current;
    if (!el) return;

    const update = () => {
      const r = el.getBoundingClientRect();
      const span = r.height - window.innerHeight;
      const p = span > 0 ? Math.min(1, Math.max(0, -r.top / span)) : 0;

      // one write on the container; every scene reads its own slice from it
      el.style.setProperty("--p", p.toFixed(5));
      for (let i = 0; i < N; i++) {
        const local = p * N - i;
        const clamped = Math.max(-1.2, Math.min(1.2, local));
        el.style.setProperty(`--z${i}`, clamped.toFixed(4));
        el.style.setProperty(`--s${i}`, Math.pow(2, clamped).toFixed(4));
        // fade in −1 → −0.55, hold, fade out 0.55 → 1
        const a =
          clamped <= -1 || clamped >= 1
            ? 0
            : clamped < -0.55
              ? (clamped + 1) / 0.45
              : clamped > 0.55
                ? (1 - clamped) / 0.45
                : 1;
        el.style.setProperty(`--o${i}`, Math.max(0, Math.min(1, a)).toFixed(4));
      }
    };

    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [N]);

  // Reduced motion gets the landscapes as an ordinary stack — same content,
  // no flight, nothing fighting the reader's setting.
  if (REDUCED) {
    return (
      <div className="zs-static">
        {scenes.map((s) => (
          <section className="zs-flat" key={s.id}>
            <div className="zs-flat-art">{s.layers}</div>
            <div className="zs-copy">
              <SceneCopy scene={s} />
            </div>
          </section>
        ))}
      </div>
    );
  }

  return (
    <section
      className="zs"
      ref={ref}
      style={{ height: `${Math.max(2, N * screensPerScene)}00vh` } as CSSProperties}
    >
      <div className="zs-pin">
        <div className="zs-stage">
          {scenes.map((s, i) => (
            <div
              className="zs-scene"
              key={s.id}
              style={
                {
                  "--s": `var(--s${i})`,
                  "--o": `var(--o${i})`,
                  zIndex: N - i,
                } as CSSProperties
              }
              aria-hidden="true"
            >
              {s.layers}
            </div>
          ))}
        </div>

        {/* copy is NOT scaled — it would become unreadable mid-flight.
            It crossfades on the same schedule as its landscape. */}
        <div className="zs-copylayer">
          {scenes.map((s, i) => (
            <div
              className="zs-copy"
              key={s.id}
              style={{ "--o": `var(--o${i})`, zIndex: N - i } as CSSProperties}
            >
              <SceneCopy scene={s} />
            </div>
          ))}
        </div>

        <Progress count={N} />
      </div>
    </section>
  );
}

function SceneCopy({ scene }: { scene: ZoomScene }) {
  return (
    <>
      <div className="zs-mark">
        <span>{`{ ${scene.n} · ${scene.place.toUpperCase()} }`}</span>
        {scene.placeTa && <span className="zs-ta">{scene.placeTa}</span>}
      </div>
      <h2 className="zs-title">
        {scene.title.split("\n").map((line, i) => (
          <span key={i}>{line}</span>
        ))}
      </h2>
      {scene.lede && <p className="zs-lede">{scene.lede}</p>}
      {scene.meta && <p className="zs-meta">{scene.meta}</p>}
    </>
  );
}

/** Where you are in the flight, and how far is left. */
function Progress({ count }: { count: number }) {
  return (
    <div className="zs-prog" aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <i key={i} style={{ "--o": `var(--o${i})` } as CSSProperties} />
      ))}
    </div>
  );
}
