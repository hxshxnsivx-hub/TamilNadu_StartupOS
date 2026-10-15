/* MERIDIAN motion primitives.
   The grammar is: uncover (Wipe), set type (SetLines), draw a rule (Rule),
   measure (Figure), lean toward the pointer (Magnetic). All CSS-driven —
   these only decide when a class lands, so reduced-motion readers get the
   resolved state with no work performed. */

import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";

const REDUCED =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** Adds `is-in` once the element has scrolled into view, then stops watching. */
function useInView<T extends HTMLElement>(threshold = 0.15) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(REDUCED);

  useEffect(() => {
    if (REDUCED) return;
    const el = ref.current;
    if (!el) return;

    // Wipes and masks hide their content until `is-in` lands, so a missed
    // observer callback would erase the page. Always resolve, even if late.
    const failsafe = setTimeout(() => setInView(true), 1600);

    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return () => clearTimeout(failsafe);
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
      io.disconnect();
    };
  }, [threshold]);

  return [ref, inView] as const;
}

const d = (delay: number) => ({ "--d": `${delay}ms` }) as CSSProperties;

/** Uncovers its children with a clip-path wipe. */
export function Wipe({
  children,
  dir = "right",
  delay = 0,
  className,
}: {
  children: ReactNode;
  dir?: "right" | "up" | "down";
  delay?: number;
  className?: string;
}) {
  const [ref, inView] = useInView<HTMLDivElement>();
  return (
    <div
      ref={ref}
      data-wipe={dir === "right" ? "" : dir}
      className={[className, inView ? "is-in" : ""].filter(Boolean).join(" ")}
      style={delay ? d(delay) : undefined}
    >
      {children}
    </div>
  );
}

/** Sets lines of type, each rising from behind its own mask. */
export function SetLines({
  lines,
  as: Tag = "h2",
  className,
  stagger = 90,
  delay = 0,
}: {
  lines: ReactNode[];
  as?: "h1" | "h2" | "h3" | "p" | "div";
  className?: string;
  stagger?: number;
  delay?: number;
}) {
  const [ref, inView] = useInView<HTMLHeadingElement>();
  const Element = Tag as "h2";
  return (
    <Element
      ref={ref as React.RefObject<HTMLHeadingElement>}
      className={[className, inView ? "is-in" : ""].filter(Boolean).join(" ")}
    >
      {lines.map((line, i) => (
        <span className="mx-line" key={i}>
          <span style={d(delay + i * stagger)}>{line}</span>
        </span>
      ))}
    </Element>
  );
}

/** A hairline that draws itself left to right when it comes into view. */
export function Rule({ ink = false, delay = 0 }: { ink?: boolean; delay?: number }) {
  const [ref, inView] = useInView<HTMLDivElement>(0.01);
  return (
    <div
      ref={ref}
      className={["mx-rule", ink ? "mx-rule-ink" : "", inView ? "is-in" : ""]
        .filter(Boolean)
        .join(" ")}
      style={delay ? d(delay) : undefined}
    />
  );
}

/**
 * A measured figure. Each digit is a column that rolls to its value, so the
 * number reads as an instrument settling rather than text appearing.
 */
export function Figure({
  value,
  prefix = "",
  suffix = "",
  delay = 0,
  className,
}: {
  value: number;
  prefix?: string;
  suffix?: string;
  delay?: number;
  className?: string;
}) {
  // Rolls on mount rather than on intersection. An observer that never fires
  // would leave the odometer resting on 0 — showing a *wrong number*, which is
  // far worse than showing the right one without the roll. Here the only
  // failure mode is a missing animation; the value is always correct.
  const [rolled, setRolled] = useState(REDUCED);
  useEffect(() => {
    if (REDUCED) return;
    // A task, not a frame: requestAnimationFrame is tied to the compositor and
    // never fires in a tab that isn't painting, which would strand the odometer
    // on 0. A timeout always runs, so the value always arrives.
    const t = setTimeout(() => setRolled(true), 32);
    return () => clearTimeout(t);
  }, [value]);

  const digits = String(Math.max(0, Math.round(value))).split("");

  return (
    <span className={["mx-fig", className].filter(Boolean).join(" ")}>
      {prefix}
      {digits.map((digit, i) => (
        <span className="mx-digits" key={i} aria-hidden="true">
          <span
            className="mx-digit"
            style={{
              ...d(delay + i * 70),
              transform: rolled ? `translateY(-${Number(digit)}em)` : "translateY(0)",
            }}
          >
            {Array.from({ length: 10 }, (_, n) => (
              <span key={n} style={{ display: "block", height: "1em" }}>
                {n}
              </span>
            ))}
          </span>
        </span>
      ))}
      <span className="sr-only">{value}</span>
      {suffix}
    </span>
  );
}

/** Leans toward the pointer, then returns. Pointer-precision devices only. */
export function Magnetic({
  children,
  strength = 0.28,
  className,
}: {
  children: ReactNode;
  strength?: number;
  className?: string;
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
    <span ref={ref} className={["mx-mag", className].filter(Boolean).join(" ")}>
      {children}
    </span>
  );
}

/** The one ambient element in this system: a still 12-column measure. */
export function MeasureGrid() {
  return <div className="mx-grid" aria-hidden="true" />;
}
