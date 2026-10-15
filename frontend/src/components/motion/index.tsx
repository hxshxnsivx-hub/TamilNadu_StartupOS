/**
 * Motion primitives.
 *
 * Ported from Bharath-tax-mitra, which had already solved the two failure
 * modes this project hit independently — worth stating plainly, because
 * both are invisible until they bite:
 *
 *   1. IntersectionObserver does not fire in a tab that is not painting.
 *      `whileInView` content therefore sticks at opacity 0 forever in a
 *      backgrounded or prerendered tab. Above-the-fold content MUST use
 *      mode="mount" — see Reveal.
 *   2. requestAnimationFrame is suspended on hidden pages for the same
 *      reason, so a rAF-driven tilt loop never starts. TiltCard writes
 *      transforms directly and lets a CSS transition do the smoothing.
 *
 * Built on LazyMotion + the `domAnimation` feature subset: ~15KB gz lands
 * in the bundle instead of the full library. Every primitive animates
 * transform/opacity ONLY (GPU-composited — smooth on the low-end devices
 * this product targets) and degrades to static under reduced motion.
 */

import {
  LazyMotion,
  domAnimation,
  m,
  AnimatePresence,
  useReducedMotion,
} from "motion/react";
import * as React from "react";

/** Wrap once near the app root. Provides the lazy feature bundle. */
export function MotionProvider({ children }: { children: React.ReactNode }) {
  return (
    <LazyMotion features={domAnimation} strict>
      {children}
    </LazyMotion>
  );
}

/* ── Entrance reveals ───────────────────────────────────────────────────── */

interface RevealProps {
  children: React.ReactNode;
  /** Stagger delay in seconds (use index * 0.08 for lists). */
  delay?: number;
  /** Slide distance in px (translateY). */
  y?: number;
  className?: string;
  /**
   * 'mount'  — animate immediately. REQUIRED above the fold.
   * 'scroll' — animate on scroll into view. Below the fold only.
   */
  mode?: "mount" | "scroll";
}

/** Fade-up entrance. The base move for everything that arrives. */
export function Reveal({
  children,
  delay = 0,
  y = 24,
  className,
  mode = "scroll",
}: RevealProps) {
  const reduce = useReducedMotion();
  const initial = reduce ? false : { opacity: 0, y };
  const target = { opacity: 1, y: 0 };
  const transition = {
    duration: 0.5,
    delay,
    ease: [0.21, 0.47, 0.32, 0.98] as const,
  };

  if (mode === "mount") {
    return (
      <m.div className={className} initial={initial} animate={target} transition={transition}>
        {children}
      </m.div>
    );
  }
  return (
    <m.div
      className={className}
      initial={initial}
      whileInView={target}
      viewport={{ once: true, margin: "-40px" }}
      transition={transition}
    >
      {children}
    </m.div>
  );
}

/* ── 3D tilt card ───────────────────────────────────────────────────────── */

interface TiltCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  /** Max tilt in degrees. Keep ≤ 8 — this is depth, not a toy. */
  maxTilt?: number;
}

/**
 * Pointer-tracked 3D tilt (perspective + rotateX/rotateY).
 *
 * Direct DOM transform writes with a CSS transition for the settle: no
 * React re-render per pointer event, and no rAF (see the header note).
 * Disabled under reduced motion and for non-mouse pointers — touch tilt
 * would fight the scroll.
 */
export function TiltCard({ children, maxTilt = 6, className, ...rest }: TiltCardProps) {
  const reduce = useReducedMotion();
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const el = ref.current;
    if (!el || reduce) return;

    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== "mouse") return;
      const rect = el.getBoundingClientRect();
      const px = (e.clientX - rect.left) / rect.width - 0.5;
      const py = (e.clientY - rect.top) / rect.height - 0.5;
      el.style.transition = "transform 80ms ease-out";
      el.style.transform = `rotateX(${(-py * maxTilt * 2).toFixed(2)}deg) rotateY(${(px * maxTilt * 2).toFixed(2)}deg)`;
    };

    const onLeave = () => {
      el.style.transition = "transform 450ms cubic-bezier(0.22, 1, 0.36, 1)";
      el.style.transform = "rotateX(0deg) rotateY(0deg)";
    };

    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerleave", onLeave);
    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", onLeave);
    };
  }, [reduce, maxTilt]);

  return (
    <div style={{ perspective: 900 }} className={className}>
      <div ref={ref} style={{ transformStyle: "preserve-3d" }} {...rest}>
        {children}
      </div>
    </div>
  );
}

/* ── Step transition ────────────────────────────────────────────────────── */

interface StepTransitionProps {
  /** Key that changes per step — drives exit/enter. */
  stepKey: string;
  /** +1 forward, -1 backward — sets the slide direction. */
  direction?: 1 | -1;
  children: React.ReactNode;
}

/**
 * Direction-aware horizontal slide + fade between steps. Forward slides
 * left, back slides right — so the motion tells you which way you moved
 * through the flow, which a plain crossfade cannot.
 */
export function StepTransition({ stepKey, direction = 1, children }: StepTransitionProps) {
  const reduce = useReducedMotion();
  return (
    <AnimatePresence mode="wait" initial={false}>
      <m.div
        key={stepKey}
        initial={reduce ? false : { opacity: 0, x: 32 * direction }}
        animate={{ opacity: 1, x: 0 }}
        exit={reduce ? undefined : { opacity: 0, x: -24 * direction }}
        transition={{ duration: 0.28, ease: [0.32, 0.72, 0, 1] }}
      >
        {children}
      </m.div>
    </AnimatePresence>
  );
}

/* ── Pressable ──────────────────────────────────────────────────────────── */

/** Scale-on-press wrapper for CTAs (spring settle, tap feedback). */
export function Pressable({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <m.div
      className={className}
      whileHover={reduce ? undefined : { scale: 1.02 }}
      whileTap={reduce ? undefined : { scale: 0.97 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
    >
      {children}
    </m.div>
  );
}

// Re-exported so consumers needing raw primitives (progress bars, SVG path
// draws) do not import `motion/react` directly and bypass LazyMotion.
// eslint-disable-next-line react-refresh/only-export-components
export { m, AnimatePresence, useReducedMotion };
