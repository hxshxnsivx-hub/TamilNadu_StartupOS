/* ============================================================
   ATELIER — the primitive set every page is built from.
   ============================================================

   The problem this solves is density, not decoration. Every card
   in this product carries the same awkward shape: an identity
   block, one or two scores, a variable-length list of reasons,
   and a provenance stamp — and it has to hold all of that in
   Tamil, at 375px, over 2G. Nine pages were each solving that
   privately, which is why the app read as nine products.

   So the card is solved once, here, and the pages compose it.

   Structural grammar, from the art research:
     · Plate    korvai — border and body are different fabrics
                interlocked at a hard edge. Accent : body = 1 : 6.
     · Register Paniker's compartmented field — unequal cells,
                shared hairlines, no gutters, one quadrant empty.
     · Shelf    thinnai — the raised platform at the street edge
                where the merchant actually did business. Actions
                live here.
     · Hara     the parapet of miniature shrines: kuta, panjara,
                sala, panjara, kuta. A divider that is South Indian
                without a single figure.
     · Rail     the ther procession — a tall stack moving laterally
                and slowly. Buys narrative length without page length.
   ============================================================ */

import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { Link } from "react-router-dom";
import { KolamKnot } from "../components/Athangudi";

const REDUCED =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

const cx = (...v: Array<string | false | undefined>) => v.filter(Boolean).join(" ");
const delay = (ms: number) => ({ "--d": `${ms}ms` }) as CSSProperties;

/* ------------------------------------------------------------------ *
 * useInView — adds `is-in` once, then stops watching.
 *
 * Carries a failsafe: masks hide their content until `is-in` lands, so a
 * missed observer callback would erase the page. Always resolve, even late.
 * ------------------------------------------------------------------ */
function useInView<T extends HTMLElement>(threshold = 0.12) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(REDUCED);
  const [settled, setSettled] = useState(REDUCED);

  useEffect(() => {
    if (REDUCED) return;
    const el = ref.current;
    if (!el) return;

    // Two independent guarantees, because reveals hide content until they
    // resolve and a stranded card is a missing scheme, not a missing effect:
    //
    //  1. `inView` always lands, observer or no observer (1600 ms failsafe).
    //  2. `settled` lands at 2200 ms no matter what, and CSS uses it to force
    //     the end state with transitions switched OFF. By then any legitimate
    //     reveal (620 ms plus at most ~440 ms of stagger) is long finished, so
    //     this is invisible on the happy path — but if the transition never
    //     ran at all, on a device that dropped the compositor or in a tab that
    //     is not painting, the content still resolves. Motion may make
    //     something smoother; it must never be the only thing that makes it
    //     correct.
    const failsafe = setTimeout(() => setInView(true), 1600);
    const resolve = setTimeout(() => setSettled(true), 2200);

    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return () => {
        clearTimeout(failsafe);
        clearTimeout(resolve);
      };
    }

    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setInView(true);
          io.disconnect();
        }
      },
      { threshold, rootMargin: "0px 0px -6% 0px" },
    );
    io.observe(el);
    return () => {
      clearTimeout(failsafe);
      clearTimeout(resolve);
      io.disconnect();
    };
  }, [threshold]);

  return [ref, inView, settled] as const;
}

/* ================================================================== *
 * PAGE — the outermost wrapper.
 *
 * Sets the route's pigment (two chromatics per surface, never three) and
 * replays the entrance cut. `tone` feeds the wall; `set` feeds the page's
 * own accents.
 * ================================================================== */

export function Page({
  set,
  className,
  children,
}: {
  set: "ideate" | "schemes" | "b2b" | "funding" | "account" | "home";
  className?: string;
  children: ReactNode;
}) {
  /* Deliberately no `data-tone` here. useWallTone picks whichever tagged
     element owns the viewport's centre line, and this wrapper spans the whole
     document — so tagging it would make it win at every scroll position and
     the wall would never retint. Tone belongs on the bands, which is where
     the reader actually is. */
  return (
    <div className={cx("v-page", className)} data-tone-set={set}>
      {children}
    </div>
  );
}

/* ================================================================== *
 * MASTHEAD — every page opens the same way.
 *
 * Index mark, display line, Tamil line, lede, actions, then the one heavy
 * horizontal in the composition. A façade with two heavy horizontals reads
 * as two buildings, so no band below this may use a cornice rule.
 * ================================================================== */

export function Masthead({
  index,
  status,
  lines,
  ta,
  lede,
  actions,
  aside,
  tone = "base",
  bleed,
}: {
  index: string;
  status?: ReactNode;
  lines: ReactNode[];
  ta?: string;
  lede?: ReactNode;
  actions?: ReactNode;
  aside?: ReactNode;
  tone?: string;
  /** Let the display line run past the page margin and be cut by the
      viewport. Landing page only — it reads as confidence exactly once. */
  bleed?: boolean;
}) {
  return (
    <header className={cx("v-mast", bleed && "is-bleed")} data-tone={tone}>
      <div className="v-mast-main">
        <div className="v-index">
          <i />
          <span>{index}</span>
          {status ? (
            <>
              <span className="v-index-sep">/</span>
              <span>{status}</span>
            </>
          ) : null}
        </div>

        <Setting as="h1" className="v-display" lines={lines} stagger={110} />

        {ta ? (
          <Uncover delay={320}>
            <p className="v-mast-ta" lang="ta">
              {ta}
            </p>
          </Uncover>
        ) : null}

        {lede ? (
          <Uncover delay={420}>
            <p className="v-lede">{lede}</p>
          </Uncover>
        ) : null}

        {actions ? (
          <Uncover delay={520}>
            <Shelf>{actions}</Shelf>
          </Uncover>
        ) : null}
      </div>

      {aside ? <div className="v-mast-aside">{aside}</div> : null}

      <Cornice />
    </header>
  );
}

/* ================================================================== *
 * BAND — a section on the diminution ladder.
 *
 * Chettinad courtyards step down by r ≈ 0.8 from the entrance inward.
 * `depth` picks the rung, so a page tightens as the reader gets further
 * in rather than marching at one pitch all the way down.
 * ================================================================== */

export function Band({
  depth = 1,
  title,
  index,
  tone,
  wide,
  invert,
  folio,
  className,
  children,
}: {
  depth?: 0 | 1 | 2 | 3;
  title?: ReactNode[];
  index?: ReactNode;
  tone?: string;
  wide?: boolean;
  /** Full-bleed inverted ground. See the note in atelier.css — at most one
      per page, and it must be the page's most important claim. */
  invert?: boolean;
  /** A folio number set in the margin, the way a book numbers a page. */
  folio?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section
      className={cx("v-band", (wide || invert) && "is-wide", invert && "is-invert", className)}
      data-depth={depth}
      data-tone={tone}
    >
      {folio ? (
        <span className="v-folio" aria-hidden="true">
          {folio}
        </span>
      ) : null}
      {title || index ? (
        <div className="v-band-head">
          {title ? <Setting as="h2" className="v-band-t" lines={title} /> : <span />}
          {index ? <span className="v-band-i">{index}</span> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}

/* ================================================================== *
 * REGISTER — the Paniker compartmented field. This is the bento.
 *
 * Rules from the source, and they are what make it read as composed
 * rather than merely gridded:
 *   · cells are UNEQUAL — no repeated module
 *   · cells share hairlines; there are no gutters and no shadows
 *   · one region of the field stays near-empty
 *
 * `span` on a Cell is in 12ths; `tall` doubles its row span.
 * ================================================================== */

export function Register({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  const [ref, inView, settled] = useInView<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={cx("v-register", inView && "is-in", settled && "is-set", className)}
    >
      {children}
    </div>
  );
}

export function Cell({
  span = 4,
  tall,
  quiet,
  label,
  className,
  children,
}: {
  span?: number;
  tall?: boolean;
  quiet?: boolean;
  label?: ReactNode;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <div
      className={cx("v-cell", tall && "is-tall", quiet && "is-quiet", className)}
      style={{ "--span": span } as CSSProperties}
    >
      {label ? <span className="v-cell-l">{label}</span> : null}
      {children}
    </div>
  );
}

/* ================================================================== *
 * PLATE — the universal card.
 *
 * Solved once because every card in this product has the same shape:
 * identity, score, reasons, provenance. `tone` sets the korvai edge —
 * the accent is a different fabric interlocked at a hard boundary, so
 * it never fades into the body.
 * ================================================================== */

export function Plate({
  tone,
  off,
  index,
  className,
  children,
}: {
  tone?: string;
  off?: boolean;
  index?: number;
  className?: string;
  children: ReactNode;
}) {
  const [ref, inView, settled] = useInView<HTMLElement>(0.06);
  return (
    <article
      ref={ref}
      className={cx(
        "v-plate",
        off && "is-off",
        inView && "is-in",
        settled && "is-set",
        className,
      )}
      style={
        {
          ...(tone ? { "--tone": tone } : {}),
          ...(index != null ? delay(Math.min(index, 7) * 62) : {}),
        } as CSSProperties
      }
    >
      <i className="v-plate-edge" aria-hidden="true" />
      {children}
    </article>
  );
}

export function PlateHead({
  eyebrow,
  title,
  meta,
  figure,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  meta?: ReactNode;
  figure?: ReactNode;
}) {
  return (
    <div className="v-plate-head">
      <div className="v-plate-id">
        {eyebrow ? <div className="v-plate-eyebrow">{eyebrow}</div> : null}
        <h4 className="v-plate-t">{title}</h4>
        {meta ? <div className="v-plate-meta">{meta}</div> : null}
      </div>
      {figure ? <div className="v-plate-fig">{figure}</div> : null}
    </div>
  );
}

/* ================================================================== *
 * REASONS — the explainability payload.
 *
 * No card in this product is a bare score: every result names the rule
 * it cleared, and every refusal names the rule it failed. That means
 * layout must always reserve room for a list of unknown length, which
 * is exactly what the pages kept getting wrong.
 * ================================================================== */

export function Reasons({
  label,
  items,
  refusal,
}: {
  label: ReactNode;
  items: string[];
  refusal?: boolean;
}) {
  if (!items?.length) return null;
  return (
    <div className={cx("v-reasons", refusal && "is-refusal")}>
      <div className="v-reasons-h">{label}</div>
      <ul>
        {items.map((r, i) => (
          <li key={i}>
            <i aria-hidden="true" />
            <span>{r}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Short reasons as chips rather than a list — for dense grids. */
export function Chips({ items }: { items: string[] }) {
  if (!items?.length) return null;
  return (
    <div className="v-chips">
      {items.map((w, i) => (
        <span className="v-chip" key={i}>
          {w}
        </span>
      ))}
    </div>
  );
}

/* ================================================================== *
 * PROVENANCE — every externally sourced fact carries its source and date.
 * Set as a running metadata band, the way an inscription wraps a wall.
 * ================================================================== */

export function Provenance({
  href,
  children,
}: {
  href?: string;
  children: ReactNode;
}) {
  const body = (
    <>
      <span>{children}</span>
      {href ? <i aria-hidden="true">↗</i> : null}
    </>
  );
  return href ? (
    <a className="v-prov" href={href} target="_blank" rel="noreferrer">
      {body}
    </a>
  ) : (
    <span className="v-prov">{body}</span>
  );
}

/* ================================================================== *
 * DIAL — a score as an arc, with its value in tabular figures.
 *
 * Counts on a timeout rather than a frame loop. An observer or rAF that
 * never fires would leave the dial resting on 0 — showing a *wrong
 * number*, which is far worse than showing the right one without motion.
 * ================================================================== */

export function useCount(target: number, ms = 900) {
  const [n, setN] = useState(REDUCED ? target : 0);
  useEffect(() => {
    if (REDUCED) {
      setN(target);
      return;
    }
    const steps = 26;
    const step = ms / steps;
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      // ease-out so it settles like an instrument rather than a counter
      const p = 1 - Math.pow(1 - i / steps, 3);
      setN(Math.round(target * p));
      if (i >= steps) {
        setN(target);
        clearInterval(id);
      }
    }, step);
    return () => clearInterval(id);
  }, [target, ms]);
  return n;
}

const clamp = (v: number) => Math.max(0, Math.min(100, Math.round(Number(v) || 0)));

/** Warm when strong, cool when not. Three bands, no gradient between them. */
export const bandOf = (v: number) => (v >= 70 ? "high" : v >= 45 ? "mid" : "low");

export function Dial({
  value,
  caption,
  size = 68,
}: {
  value: number;
  caption: string;
  size?: number;
}) {
  const target = clamp(value);
  const n = useCount(target, 1000);
  const stroke = 4;
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;

  return (
    <div className={cx("v-dial", `is-${bandOf(target)}`)}>
      <div className="v-dial-face" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          role="img"
          aria-label={`${caption} ${target} of 100`}
        >
          <circle
            className="v-dial-track"
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            strokeWidth={stroke}
          />
          <circle
            className="v-dial-val"
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            strokeWidth={stroke}
            strokeDasharray={circ}
            strokeDashoffset={circ * (1 - n / 100)}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />
        </svg>
        <span className="v-dial-n" aria-hidden="true">
          {n}
        </span>
      </div>
      <span className="v-dial-cap">{caption}</span>
    </div>
  );
}

/** A supporting measure — same vocabulary as the dial, laid flat. */
export function Meter({
  label,
  value,
  index = 0,
}: {
  label: string;
  value: number;
  index?: number;
}) {
  const target = clamp(value);
  const n = useCount(target, 850);
  return (
    <div
      className={cx("v-meter", `is-${bandOf(target)}`)}
      style={delay(index * 62)}
    >
      <span className="v-meter-l">{label}</span>
      <span className="v-meter-track">
        <span className="v-meter-fill" style={{ width: `${target}%` }} />
      </span>
      <span className="v-meter-v">{n}</span>
    </div>
  );
}

/* ================================================================== *
 * SPIDER — six axes at once.
 *
 * A radar plot is the wrong default for most data, but it is right here:
 * the six readiness dimensions are a fixed set, on one shared 0–100 scale,
 * and the question a founder actually asks is "which side am I weak on",
 * which is a shape question. Six bars answer "how big is each"; the polygon
 * answers "what am I lopsided toward".
 *
 * Twelve-fold geometry is the project's rotational constant, so six axes at
 * 60° sit on it exactly.
 *
 * The polygon is not the only encoding — every axis is also labelled with
 * its number, because a shape alone is not readable to a screen reader and
 * is hard to compare precisely.
 * ================================================================== */

export function Spider({
  axes,
  size = 260,
}: {
  axes: Array<{ label: string; value: number }>;
  size?: number;
}) {
  const n = axes.length;
  if (!n) return null;

  const c = size / 2;
  const r = c * 0.66;
  const pt = (i: number, frac: number) => {
    // start at 12 o'clock and go clockwise, so the first axis reads first
    const a = (Math.PI * 2 * i) / n - Math.PI / 2;
    return [c + Math.cos(a) * r * frac, c + Math.sin(a) * r * frac] as const;
  };

  const rings = [0.25, 0.5, 0.75, 1];
  const web = rings.map((f) =>
    axes.map((_, i) => pt(i, f).map((v) => v.toFixed(1)).join(",")).join(" "),
  );
  const shape = axes
    .map((a, i) =>
      pt(i, Math.max(0, Math.min(100, a.value)) / 100)
        .map((v) => v.toFixed(1))
        .join(","),
    )
    .join(" ");

  return (
    <div className="v-spider">
      <svg
        viewBox={`0 0 ${size} ${size}`}
        width={size}
        height={size}
        role="img"
        aria-label={axes
          .map((a) => `${a.label.replace(/_/g, " ")} ${Math.round(a.value)} of 100`)
          .join(", ")}
      >
        <g className="v-spider-web" fill="none">
          {web.map((p, i) => (
            <polygon key={i} points={p} />
          ))}
          {axes.map((_, i) => {
            const [x, y] = pt(i, 1);
            return <line key={i} x1={c} y1={c} x2={x} y2={y} />;
          })}
        </g>

        <polygon className="v-spider-shape" points={shape} />

        {axes.map((a, i) => {
          const [x, y] = pt(i, Math.max(0, Math.min(100, a.value)) / 100);
          return <circle key={i} className="v-spider-dot" cx={x} cy={y} r={2.6} />;
        })}
      </svg>

      {/* the numbers, because the polygon is a shape and a shape is not a value */}
      <ol className="v-spider-key">
        {axes.map((a, i) => (
          <li key={a.label}>
            <span className="v-spider-key-n">{String(i + 1).padStart(2, "0")}</span>
            <span className="v-spider-key-l">{a.label.replace(/_/g, " ")}</span>
            <b className={cx("v-spider-key-v", `is-${bandOf(a.value)}`)}>
              {Math.round(a.value)}
            </b>
          </li>
        ))}
      </ol>
    </div>
  );
}

/* ================================================================== *
 * STAT — a measured figure. Numerals are set as instrument readings:
 * tabular, oversized, tracked tight.
 * ================================================================== */

export function Stat({
  label,
  value,
  suffix,
  index = 0,
}: {
  label: ReactNode;
  value: number;
  suffix?: string;
  index?: number;
}) {
  const n = useCount(value, 900);
  return (
    <dl className="v-stat" style={delay(index * 90)}>
      <dt>{label}</dt>
      <dd>
        {n}
        {suffix ? <i>{suffix}</i> : null}
      </dd>
    </dl>
  );
}

/* ================================================================== *
 * SHELF — thinnai. The raised platform at the street edge, which is
 * where the merchant actually did business. Primary actions live on it.
 * ================================================================== */

export function Shelf({
  note,
  children,
}: {
  note?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="v-shelf">
      <div className="v-shelf-actions">{children}</div>
      {note ? <span className="v-shelf-note">{note}</span> : null}
    </div>
  );
}

/* ================================================================== *
 * CORNICE / HARA — the two dividers.
 *
 * Cornice is the one heavy horizontal, maximum two per page. Hara is the
 * parapet: kuta – panjara – sala – panjara – kuta, in the sourced widths
 * (0.18 / 0.11 / 0.26 / 0.11 / 0.18 of the run) and heights (0.92 / 0.62
 * / 1.0). Unmistakably South Indian without a single figure or deity.
 * ================================================================== */

export function Cornice() {
  const [ref, inView, settled] = useInView<HTMLDivElement>(0.01);
  return (
    <div
      ref={ref}
      className={cx("v-cornice", inView && "is-in", settled && "is-set")}
    />
  );
}

export function Hara({ className }: { className?: string }) {
  return (
    <svg
      className={cx("v-hara", className)}
      viewBox="0 0 100 24"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <g fill="currentColor">
        {/* kuta (square, domed) — 0.18 run, 0.92 height, at both ends */}
        <rect x="0" y="2" width="18" height="22" />
        <rect x="82" y="2" width="18" height="22" />
        {/* panjara (small barrel niche) — 0.11 run, 0.62 height */}
        <rect x="22" y="9" width="11" height="15" />
        <rect x="67" y="9" width="11" height="15" />
        {/* sala (barrel vault, centre) — 0.26 run, full height */}
        <rect x="37" y="0" width="26" height="24" />
        {/* harantara — the recessed links, 0.25h below the aedicule tops */}
        <rect x="18" y="18" width="4" height="6" />
        <rect x="33" y="18" width="4" height="6" />
        <rect x="63" y="18" width="4" height="6" />
        <rect x="78" y="18" width="4" height="6" />
      </g>
    </svg>
  );
}

/** A rule that stops short of the margin — the cheapest gesture that
    signals a composed surface rather than a table. */
export function FreeRule({ delay: d = 0 }: { delay?: number }) {
  const [ref, inView, settled] = useInView<HTMLDivElement>(0.01);
  return (
    <div
      ref={ref}
      className={cx("v-freerule", inView && "is-in", settled && "is-set")}
      style={d ? delay(d) : undefined}
    />
  );
}

/* ================================================================== *
 * SETTING / UNCOVER — type arriving.
 *
 * Both only decide when a class lands; CSS does the work. Reduced-motion
 * readers get the resolved state with nothing performed.
 * ================================================================== */

export function Setting({
  lines,
  as: Tag = "h2",
  className,
  stagger = 90,
  delay: d = 0,
}: {
  lines: ReactNode[];
  as?: "h1" | "h2" | "h3" | "p" | "div";
  className?: string;
  stagger?: number;
  delay?: number;
}) {
  const [ref, inView, settled] = useInView<HTMLHeadingElement>();
  const El = Tag as "h2";
  return (
    <El
      ref={ref as React.RefObject<HTMLHeadingElement>}
      className={cx("v-set", className, inView && "is-in", settled && "is-set")}
    >
      {lines.map((line, i) => (
        <span className="v-set-line" key={i}>
          <span style={delay(d + i * stagger)}>{line}</span>
        </span>
      ))}
    </El>
  );
}

export function Uncover({
  children,
  delay: d = 0,
  className,
  as: Tag = "div",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
  as?: "div" | "section" | "header" | "article";
}) {
  const [ref, inView, settled] = useInView<HTMLDivElement>();
  const El = Tag as "div";
  return (
    <El
      ref={ref as React.RefObject<HTMLDivElement>}
      className={cx("v-uncover", className, inView && "is-in", settled && "is-set")}
      style={d ? delay(d) : undefined}
    >
      {children}
    </El>
  );
}

/* ================================================================== *
 * RAIL — story mode. A pinned band whose panels advance sideways.
 *
 * n panels would normally cost n screens of vertical scroll. Pinning the
 * band and moving the track laterally spends the same scroll distance on
 * one screen of height, so a whole sequence stays legible without the
 * page becoming a corridor. Space utilisation is the point.
 *
 * Progress is written straight to a custom property on scroll and CSS
 * does the transform — no frame loop, no library, and the value is
 * directly inspectable, so the behaviour can actually be tested. Below
 * the pin breakpoint, and under reduced motion, the panels simply stack.
 * ================================================================== */

export function Rail({
  count,
  screens,
  head,
  children,
  tone,
}: {
  /** How many panels there are. Shown in the index mark. */
  count: number;
  /** How many screens of scroll to spend. Defaults to one per panel, capped
      so a 15-milestone roadmap does not become a 1500vh corridor. */
  screens?: number;
  head?: ReactNode;
  children: ReactNode;
  tone?: string;
}) {
  const ref = useRef<HTMLElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const height = Math.max(2, Math.min(screens ?? count, 6));

  useEffect(() => {
    if (REDUCED) return;
    const el = ref.current;
    const track = trackRef.current;
    if (!el || !track) return;

    // Travel is MEASURED, not derived from the panel count. Deriving it
    // assumed every panel was exactly 1/count of the track, which silently
    // under-travels the moment the panel count and the scroll height differ
    // (a capped roadmap), or a panel wraps to a different height, or the
    // clamp() on panel width resolves differently at another viewport.
    // Measuring is correct in all of those cases and costs one read.
    const update = () => {
      const r = el.getBoundingClientRect();
      const span = r.height - window.innerHeight;
      const p = span > 0 ? -r.top / span : 0;
      el.style.setProperty("--p", Math.min(1, Math.max(0, p)).toFixed(4));

      const over = track.scrollWidth - track.clientWidth;
      el.style.setProperty("--travel", `${-Math.max(0, over)}px`);
    };

    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [count, screens]);

  if (REDUCED) {
    return (
      <section className="v-rail is-static" data-tone={tone}>
        {children}
      </section>
    );
  }

  return (
    <section
      className="v-rail"
      ref={ref}
      data-tone={tone}
      style={{ height: `${height * 100}vh` } as CSSProperties}
    >
      <div className="v-rail-pin">
        <div className="v-rail-head">
          <span className="v-rail-idx">
            01 — {String(count).padStart(2, "0")}
          </span>
          {head}
          <div className="v-rail-bar">
            <i />
          </div>
        </div>
        <div className="v-rail-track" ref={trackRef}>
          {children}
        </div>
      </div>
    </section>
  );
}

export function RailPanel({
  n,
  to,
  title,
  ta,
  step,
  body,
  cta,
  tone,
}: {
  n: string;
  to?: string;
  title: ReactNode;
  ta?: string;
  step?: ReactNode;
  body: ReactNode;
  cta?: ReactNode;
  tone?: string;
}) {
  return (
    <article className="v-rail-panel" style={{ "--tone": tone } as CSSProperties}>
      <span className="v-rail-n">{n}</span>
      <h3 className="v-rail-t">{title}</h3>
      {ta ? (
        <p className="v-rail-ta" lang="ta">
          {ta}
        </p>
      ) : null}
      {step ? <span className="v-rail-step">{step}</span> : null}
      <p className="v-rail-b">{body}</p>
      {to && cta ? (
        <Link to={to} className="v-rail-go">
          {cta} <span aria-hidden="true">→</span>
        </Link>
      ) : null}
      <i className="v-rail-edge" aria-hidden="true" />
    </article>
  );
}

/* ================================================================== *
 * EMPTY — rejection as a roadmap.
 *
 * The canonical empty state in this product is not "no results". It is a
 * ranked count of what blocked you, each item paired with the thing that
 * would change it. An empty state that only says "nothing found" throws
 * away the one thing a constraint solver actually knows.
 * ================================================================== */

export function Empty({
  title,
  body,
  fixes,
}: {
  title: ReactNode;
  body?: ReactNode;
  fixes?: Array<{ label: string; count?: number }>;
}) {
  return (
    <Uncover className="v-empty">
      <span className="v-empty-mark" aria-hidden="true" />
      <p className="v-empty-t">{title}</p>
      {body ? <p className="v-empty-d">{body}</p> : null}
      {fixes?.length ? (
        <ul className="v-empty-fixes">
          {fixes.map((f, i) => (
            <li key={i}>
              <span>{f.label}</span>
              {f.count != null ? <b>{f.count}</b> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </Uncover>
  );
}

/* ================================================================== *
 * STEPPER — where you are in a short sequence.
 *
 * Drawn as discrete gates rather than a continuous bar, because the state
 * it reports is discrete. A smooth bar would claim a precision the data
 * does not have.
 * ================================================================== */

export function Stepper({
  steps,
  at,
}: {
  steps: string[];
  at: number;
}) {
  return (
    <ol className="v-stepper" aria-label={`Step ${at + 1} of ${steps.length}`}>
      {steps.map((s, i) => (
        <li
          key={s}
          className={cx(
            "v-step",
            i < at && "is-done",
            i === at && "is-here",
          )}
          aria-current={i === at ? "step" : undefined}
        >
          <span className="v-step-n">{String(i + 1).padStart(2, "0")}</span>
          <span className="v-step-l">{s}</span>
          <span className="v-step-bar" />
        </li>
      ))}
    </ol>
  );
}

/* ================================================================== *
 * CHOICE — a selectable card.
 *
 * A real radio input carries the semantics (keyboard, grouping, screen
 * reader), and the card is its label. Rebuilding that on a div would have
 * meant rebuilding arrow-key navigation and the accessible group, badly.
 * ================================================================== */

export function Choice({
  name,
  value,
  checked,
  onChange,
  label,
  ta,
  body,
  index = 0,
}: {
  name: string;
  value: string;
  checked: boolean;
  onChange: (v: string) => void;
  label: ReactNode;
  ta?: string;
  body?: ReactNode;
  index?: number;
}) {
  return (
    <label
      className={cx("v-choice", checked && "is-on")}
      style={delay(index * 62)}
    >
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        onChange={() => onChange(value)}
        className="v-sr"
      />
      <span className="v-choice-mark" aria-hidden="true" />
      <span className="v-choice-body">
        <span className="v-choice-l">{label}</span>
        {ta ? (
          <span className="v-choice-ta" lang="ta">
            {ta}
          </span>
        ) : null}
        {body ? <span className="v-choice-d">{body}</span> : null}
      </span>
      <i className="v-choice-edge" aria-hidden="true" />
    </label>
  );
}

/* ================================================================== *
 * THRESHOLD — the sign-in / sign-up surface.
 *
 * Two sourced rules do the work here:
 *   · a compound wall is a long quiet run pierced by one emphatic
 *     gateway. Auth is that gateway, so it is the only place in the
 *     product with a full arch.
 *   · the arch is SEMICIRCULAR, not segmental. Segmental arches are for
 *     content (windows, cards); semicircular ones are for thresholds.
 *     It is a real distinction in the architecture and it is free.
 *
 * The kolam on the panel is monochrome by rule. Its whole power is one
 * line at one value, and colouring it is the fastest way to turn a
 * threshold mark into a sticker.
 * ================================================================== */

export function Threshold({
  eyebrow,
  title,
  note,
  children,
}: {
  eyebrow: ReactNode;
  title: ReactNode;
  note?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="v-threshold">
      <aside className="v-thr-panel">
        <div className="v-thr-mark">
          Vanigam <b lang="ta">வணிகம்</b>
        </div>

        {/* the gateway: semicircular, because this is a threshold */}
        <svg className="v-thr-arch" viewBox="0 0 100 96" aria-hidden="true">
          <path
            d="M6 96 V50 A44 44 0 0 1 94 50 V96"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.8"
          />
          <path
            d="M14 96 V50 A36 36 0 0 1 86 50 V96"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.5"
            opacity="0.5"
          />
        </svg>

        <div className="v-thr-kolam">
          <KolamKnot size={132} dots={3} />
        </div>

        {note ? <p className="v-thr-note">{note}</p> : null}
      </aside>

      <div className="v-thr-form">
        <div className="v-index">
          <i />
          <span>{eyebrow}</span>
        </div>
        <Setting as="h2" className="v-thr-t" lines={[title]} />
        {children}
      </div>
    </div>
  );
}

/* ================================================================== *
 * WAITING — the kolam, drawing itself.
 *
 * A true kolam is one unbroken line that encircles every dot and has no
 * loose ends; the figure is complete only once every point is enclosed.
 * That is the same claim the rules engine makes about eligibility, which
 * is why this is the waiting state and not a spinner.
 *
 * Exactly one instance per surface, monochrome, low contrast. It is the
 * most recognisable Tamil motif and therefore the fastest route to
 * looking like a tourist brochure — the restraint is the whole point.
 * ================================================================== */

export function Waiting({ label }: { label: ReactNode }) {
  return (
    <div className="v-waiting" role="status" aria-live="polite">
      <KolamKnot size={104} />
      <span>{label}</span>
    </div>
  );
}

/**
 * Slabs standing where the results will land.
 *
 * Reserves the real height of a Plate so nothing below it jumps when the
 * data arrives — layout shift is the one loading cost a reader actually
 * feels on a slow connection.
 */
export function Pending({ rows = 3 }: { rows?: number }) {
  return (
    <div className="v-grid" aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => (
        <div className="v-skel" key={i} style={delay(i * 110)}>
          <div className="v-skel-row is-chip" />
          <div className="v-skel-row is-title" />
          <div className="v-skel-row" />
          <div className="v-skel-row is-short" />
          <div className="v-skel-row is-bar" />
        </div>
      ))}
    </div>
  );
}

/* ================================================================== *
 * MAGNETIC — leans toward the pointer, then returns.
 * Pointer-precision devices only; never the only affordance.
 * ================================================================== */

export function Magnetic({
  children,
  strength = 0.26,
}: {
  children: ReactNode;
  strength?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (REDUCED) return;
    if (!window.matchMedia("(pointer: fine)").matches) return;
    const el = ref.current;
    if (!el) return;

    const onMove = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      const dx = e.clientX - (r.left + r.width / 2);
      const dy = e.clientY - (r.top + r.height / 2);
      el.style.transform = `translate(${dx * strength}px, ${dy * strength}px)`;
    };
    const reset = () => {
      el.style.transform = "";
    };

    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerleave", reset);
    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", reset);
      reset();
    };
  }, [strength]);

  return (
    <span ref={ref} className="v-mag">
      {children}
    </span>
  );
}
