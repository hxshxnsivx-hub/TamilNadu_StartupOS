/* Puducherry façade + Madras Art Movement structure.
 * Geometry per .kiro/specs/tamil-nadu-startupos/art-reference-pondicherry.md
 */

/**
 * Segmental arch — the Ville Blanche window head.
 *
 * INTACH describes the façade as "flat or segmental arched windows with bands
 * and louvered wooden shutters". At the canonical rise:span of 1/6 the radius
 * resolves to exactly R = 5S/6, with the centre 2S/3 below the springing line
 * and a half-angle of 36.87° — a 3-4-5 triangle.
 *
 * For S = 100: rise = 16.667, R = 83.333, and the sagitta checks out as
 * R − √(R² − 50²) = 83.333 − 66.667 = 16.667. Stretched with
 * preserveAspectRatio="none" so it spans any width at constant depth.
 */
export function Cornice({ className = "cornice" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 100 17"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d="M0 16.667 A83.333 83.333 0 0 1 100 16.667"
        fill="none"
        stroke="currentColor"
        strokeWidth="0.6"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

/**
 * Paniker cordon field — after K.C.S. Paniker's "Words and Symbols".
 *
 * His documented method: "thin vertical and horizontal lines to cordon off
 * space on the surface of the canvas, filling it with inscrutable notes."
 * That is an editorial grid with hairline rules and deliberately UNEQUAL
 * cells — which is why it sits so naturally under this UI.
 *
 * Rules honoured here:
 *   · cells are unequal, never a uniform matrix
 *   · some rules run free — they stop short instead of meeting a corner
 *   · one quadrant is left deliberately empty
 *   · the "notes" are mark-making, never legible text
 */
export function CordonField({ className = "cordon" }: { className?: string }) {
  // unequal divisions — no repeated interval
  const vx = [17, 38, 61, 82];
  const hy = [23, 44, 71];

  // short marks standing in for the "inscrutable notes"; the lower-right
  // quadrant is left bare on purpose
  const notes: Array<[number, number, number]> = [
    [6, 10, 7],
    [6, 15, 4],
    [24, 31, 9],
    [24, 36, 5],
    [45, 12, 6],
    [45, 17, 8],
    [68, 52, 7],
    [68, 57, 4],
    [24, 78, 6],
    [6, 84, 9],
  ];

  return (
    <svg
      className={className}
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <g stroke="currentColor" strokeWidth="0.35" vectorEffect="non-scaling-stroke">
        {/* verticals — the last one runs free, stopping short of the edge */}
        {vx.map((x, i) => (
          <line key={`v${x}`} x1={x} y1={0} x2={x} y2={i === 3 ? 62 : 100} />
        ))}
        {/* horizontals — the middle one runs free from the left */}
        {hy.map((y, i) => (
          <line key={`h${y}`} x1={i === 1 ? 17 : 0} y1={y} x2={100} y2={y} />
        ))}
      </g>
      <g stroke="currentColor" strokeWidth="0.5" vectorEffect="non-scaling-stroke" opacity="0.75">
        {notes.map(([x, y, w], i) => (
          <line key={i} x1={x} y1={y} x2={x + w} y2={y} />
        ))}
      </g>
    </svg>
  );
}
