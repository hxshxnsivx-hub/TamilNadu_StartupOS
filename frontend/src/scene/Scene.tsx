/* Cinematic scroll scenes.
 *
 * Reference: a studio site where the page opens on a full-bleed sky, the scene
 * drifts as you scroll, and display type emerges over it band by band. We take
 * the *motion grammar* — pinned scene, layered parallax, masked type reveal,
 * a mono chapter mark — and put Tamil Nadu monuments in the scenery instead.
 *
 * Each Scene is a pinned band. Layers translate at different rates against a
 * single measured scroll progress, which is what produces depth: the ridge
 * behind barely moves, the foreground moves most.
 *
 * Progress is written SYNCHRONOUSLY on scroll, never in requestAnimationFrame.
 * rAF does not fire in a tab that is not painting, which would strand every
 * scene on its first frame — the same failure that once left the odometer
 * reading zero. CSS does all the transforming from `--p`.
 */

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

const REDUCED =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export type SceneProps = {
  /** Chapter mark, e.g. "01" */
  n: string;
  /** Place name shown beside the number — the city, not the monument */
  place: string;
  /** Place name in Tamil */
  placeTa?: string;
  title: ReactNode;
  lede?: ReactNode;
  body?: ReactNode;
  /** The monument backdrop */
  backdrop: ReactNode;
  /** Screens of scroll this scene costs. 1 = one viewport. */
  screens?: number;
  children?: ReactNode;
};

export function Scene({
  n,
  place,
  placeTa,
  title,
  lede,
  body,
  backdrop,
  screens = 2,
  children,
}: SceneProps) {
  const ref = useRef<HTMLElement>(null);
  const [ready, setReady] = useState(REDUCED);

  // Arm the type reveal on mount, on a task rather than a frame, and BEFORE
  // the reduced-motion bail-out. The hidden start state means anything that
  // stops this from running leaves the headline invisible — so it must not
  // depend on rAF, an observer, or scroll ever happening.
  useEffect(() => {
    if (REDUCED) return;
    const t = setTimeout(() => setReady(true), 32);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (REDUCED) return;
    const el = ref.current;
    if (!el) return;

    // one rect read, one custom-property write — cheap enough to run inline
    const update = () => {
      const r = el.getBoundingClientRect();
      const span = r.height - window.innerHeight;
      const p = span > 0 ? -r.top / span : 0;
      el.style.setProperty("--p", Math.min(1, Math.max(0, p)).toFixed(4));
    };

    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [screens]);

  return (
    <section
      className={REDUCED ? "sc sc-static" : "sc"}
      ref={ref}
      data-ready={ready ? "1" : undefined}
      style={{ "--screens": screens } as CSSProperties}
    >
      <div className="sc-pin">
        <div className="sc-stage" aria-hidden="true">
          {backdrop}
        </div>

        <div className="sc-veil" aria-hidden="true" />

        <div className="sc-content">
          <div className="sc-mark">
            <span>{`{ ${n} · ${place.toUpperCase()} }`}</span>
            {placeTa && <span className="sc-mark-ta">{placeTa}</span>}
          </div>

          <h2 className="sc-title">
            {typeof title === "string"
              ? title.split("\n").map((line, i) => (
                  <span className="sc-line" key={i}>
                    <span style={{ "--d": `${i * 90}ms` } as CSSProperties}>{line}</span>
                  </span>
                ))
              : title}
          </h2>

          {(lede || body) && (
            <div className="sc-col">
              {lede && <p className="sc-lede">{lede}</p>}
              {body && <p className="sc-body">{body}</p>}
            </div>
          )}

          {children}
        </div>
      </div>
    </section>
  );
}

/**
 * The five parallax planes every backdrop is built from, furthest first.
 * Rates are fixed here rather than per-monument so depth stays consistent
 * across the whole sequence — a scene whose hills move faster than another's
 * reads as a different world, not a different place.
 */
export function Plane({
  depth,
  children,
  className,
}: {
  /** 0 = sky (barely moves) … 4 = foreground (moves most) */
  depth: 0 | 1 | 2 | 3 | 4;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={["sc-plane", `sc-d${depth}`, className].filter(Boolean).join(" ")}
      aria-hidden="true"
    >
      {children}
    </div>
  );
}
