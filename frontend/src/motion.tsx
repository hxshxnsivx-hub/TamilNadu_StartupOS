/* Motion primitives for "Living Pigment".
   Everything here is CSS-driven — these hooks only decide *when* a class
   lands, so a reader who prefers stillness (prefers-reduced-motion) simply
   gets the end state with no work done. */

import { useEffect, useRef, useState, type ReactNode } from "react";

type Dir = "up" | "left" | "right" | "scale";

const REDUCED =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** Reveals its children once they scroll into view, then stops observing. */
export function Reveal({
  children,
  dir = "up",
  delay = 0,
  as: Tag = "div",
  className,
}: {
  children: ReactNode;
  dir?: Dir;
  delay?: number;
  as?: "div" | "section" | "article" | "li" | "header";
  className?: string;
}) {
  const ref = useRef<HTMLElement | null>(null);
  const [shown, setShown] = useState(REDUCED);

  useEffect(() => {
    if (REDUCED) return;
    const el = ref.current;
    if (!el) return;

    // Safety net. The hidden start state means a missed observer callback would
    // leave content permanently invisible — a far worse failure than a skipped
    // animation. If nothing has fired by this point, reveal regardless.
    const failsafe = setTimeout(() => setShown(true), 1600);

    if (typeof IntersectionObserver === "undefined") {
      setShown(true);
      return () => clearTimeout(failsafe);
    }

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true);
          io.disconnect();
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" },
    );
    io.observe(el);
    return () => {
      clearTimeout(failsafe);
      io.disconnect();
    };
  }, []);

  const Element = Tag as "div";
  return (
    <Element
      ref={ref as React.RefObject<HTMLDivElement>}
      data-reveal={dir}
      className={[className, shown ? "is-in" : ""].filter(Boolean).join(" ")}
      style={delay ? ({ "--reveal-delay": `${delay}ms` } as React.CSSProperties) : undefined}
    >
      {children}
    </Element>
  );
}

/** True once the page has scrolled past `offset` — used to weight the header. */
export function useStuck(offset = 8) {
  const [stuck, setStuck] = useState(false);
  useEffect(() => {
    const onScroll = () => setStuck(window.scrollY > offset);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [offset]);
  return stuck;
}

/** A hairline rail across the top showing how far down the document you are. */
export function ScrollRail() {
  const [p, setP] = useState(0);
  useEffect(() => {
    const onScroll = () => {
      const h = document.documentElement.scrollHeight - window.innerHeight;
      setP(h > 0 ? Math.min(1, window.scrollY / h) : 0);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);
  return <div className="scrollrail" style={{ "--progress": p } as React.CSSProperties} />;
}

/** Counts up to `value` — for scores that should feel measured, not printed. */
export function useCountUp(value: number, ms = 900) {
  const [n, setN] = useState(REDUCED ? value : 0);
  useEffect(() => {
    if (REDUCED) {
      setN(value);
      return;
    }
    let raf = 0;
    const t0 = performance.now();
    const from = 0;
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / ms);
      // ease-out cubic, so the number lands softly
      setN(Math.round(from + (value - from) * (1 - Math.pow(1 - k, 3))));
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value, ms]);
  return n;
}
