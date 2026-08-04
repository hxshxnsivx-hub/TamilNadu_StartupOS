/* Story mode — a pinned band whose chapters advance horizontally as you scroll.
 *
 * Four chapters would normally cost four screens of vertical scroll. Pinning
 * the band and moving the track sideways spends the same scroll distance on a
 * single screen of height, so the whole arc stays legible without the page
 * becoming a corridor. Space utilisation is the point, not the effect.
 *
 * Implementation note — why this is not `motion`'s useScroll/useSpring:
 *   motion drives every style through its own requestAnimationFrame loop. That
 *   is fine in a painting tab and completely inert in one that isn't, which
 *   makes the behaviour unverifiable and gives it the same failure mode that
 *   already stranded the odometer at 0 and the aurora on one tone. It also
 *   cost ~136 kB (44 kB gzipped) for this single effect.
 *   Here scroll position is written straight to a custom property on scroll,
 *   and CSS does the transform. No frame loop, no library, and the progress
 *   value is directly inspectable — so it can actually be tested.
 */

import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";

export type Chapter = {
  n: string;
  to: string;
  title: string;
  ta: string;
  body: string;
  tone: string;
  cta: string;
};

const REDUCED =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export default function StoryTrack({ chapters }: { chapters: Chapter[] }) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    if (REDUCED) return;
    const el = ref.current;
    if (!el) return;

    // Written synchronously: one rect read, one property write. `--p` runs
    // 0 → 1 across the pinned band; CSS turns it into travel and progress.
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
  }, [chapters.length]);

  // Reduced motion gets the same content as an ordinary stack — no pinning,
  // no horizontal travel, nothing fighting the reader's setting.
  if (REDUCED) {
    return (
      <section className="story story-static" data-tone="chapters">
        {chapters.map((c) => (
          <ChapterPanel key={c.n} c={c} isStatic />
        ))}
      </section>
    );
  }

  return (
    <section
      className="story"
      ref={ref}
      data-tone="chapters"
      style={{
        height: `${chapters.length * 100}vh`,
        // travel stops with the last panel flush to the right edge
        ["--travel" as string]: `${(-100 * (chapters.length - 1)) / chapters.length}%`,
      }}
    >
      <div className="story-pin">
        <div className="story-head">
          <span className="story-idx">
            01 — {String(chapters.length).padStart(2, "0")}
          </span>
          <div className="story-bar">
            <i />
          </div>
        </div>

        <div className="story-track">
          {chapters.map((c) => (
            <ChapterPanel key={c.n} c={c} />
          ))}
        </div>
      </div>
    </section>
  );
}

function ChapterPanel({ c, isStatic }: { c: Chapter; isStatic?: boolean }) {
  return (
    <article
      className={isStatic ? "story-panel is-static" : "story-panel"}
      style={{ ["--tone" as string]: c.tone }}
    >
      <span className="story-n">{c.n}</span>
      <h3 className="story-t">{c.title}</h3>
      <p className="story-ta">{c.ta}</p>
      <span className="story-step">Step {Number(c.n)} of 4</span>
      <p className="story-b">{c.body}</p>
      <Link to={c.to} className="story-go">
        {c.cta} <span aria-hidden="true">→</span>
      </Link>
      <i className="story-edge" />
    </article>
  );
}
