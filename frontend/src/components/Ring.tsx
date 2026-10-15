// Completeness meter (0–100). Flat pigment, butt caps.
// The arc is *drawn* on mount — and re-drawn whenever the value changes —
// by handing the stroke a full dash offset on the first frame and letting a
// CSS transition pull it back. Colour follows the band: madder → ochre → jade.
import { useEffect, useState } from "react";
import { useCountUp } from "../motion";

const REDUCED =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export type RingBand = "low" | "mid" | "high";

/** Band thresholds are shared with the pages so labels and arc always agree. */
export function ringBand(value: number): RingBand {
  return value >= 61 ? "high" : value >= 41 ? "mid" : "low";
}

const PIGMENT: Record<RingBand, string> = {
  low: "var(--madder)",
  mid: "var(--ochre)",
  high: "var(--jade)",
};

export default function Ring({
  value,
  size = 128,
  showValue = true,
  className,
}: {
  value: number;
  size?: number;
  /** Hide the numeral when the caller renders its own (e.g. a count-up hero). */
  showValue?: boolean;
  className?: string;
}) {
  const v = Math.max(0, Math.min(100, Math.round(Number(value) || 0)));
  const stroke = Math.max(8, Math.round(size * 0.08));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const band = ringBand(v);
  const shown = useCountUp(v, 1000);

  // false on the first painted frame → the arc starts empty, then transitions.
  const [drawn, setDrawn] = useState(REDUCED);
  useEffect(() => {
    if (REDUCED) {
      setDrawn(true);
      return;
    }
    setDrawn(false);
    let alive = true;
    let inner = 0;
    const outer = requestAnimationFrame(() => {
      inner = requestAnimationFrame(() => {
        if (alive) setDrawn(true);
      });
    });
    return () => {
      alive = false;
      cancelAnimationFrame(outer);
      cancelAnimationFrame(inner);
    };
  }, [v]);

  const off = drawn ? c * (1 - v / 100) : c;

  return (
    <svg
      className={["ring", "jr-ring", `jr-ring-${band}`, className].filter(Boolean).join(" ")}
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label={`${v}%`}
    >
      <circle
        className="ring-track"
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="var(--carbon-3)"
        strokeWidth={stroke}
      />
      <circle
        className="ring-value"
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={PIGMENT[band]}
        strokeWidth={stroke}
        strokeDasharray={c}
        strokeDashoffset={off}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      {showValue && (
        <text
          x="50%"
          y="50%"
          dominantBaseline="central"
          textAnchor="middle"
          fontSize={size * 0.3}
          fontWeight="700"
          fontFamily="var(--mono)"
          fill="var(--chalk)"
        >
          {shown}
        </text>
      )}
    </svg>
  );
}
