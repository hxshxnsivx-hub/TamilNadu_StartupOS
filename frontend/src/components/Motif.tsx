// Pulli kolam lattice — static geometry. Dots, diamond rule, registration marks.
// Systematic repetition; no motion, no gradient.
//
// Below the default motif live the larger decorative fields used as background
// layers on the landing page. All of them are pure inline SVG, aria-hidden,
// and stroke only with palette variables.

const DOTS = [30, 90, 150, 210, 270];

export default function Motif() {
  return (
    <svg className="motif" viewBox="0 0 300 300" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      {/* field rule */}
      <rect x="0.5" y="0.5" width="299" height="299" fill="none" stroke="var(--rule)" strokeWidth="1" />

      {/* dot matrix — the pulli */}
      {DOTS.map((y) =>
        DOTS.map((x) => <circle key={`${x}-${y}`} cx={x} cy={y} r="1.75" fill="var(--chalk-dim)" />),
      )}

      {/* diamond lattice drawn around the dots */}
      <g fill="none" stroke="var(--madder)" strokeWidth="1.25">
        <path d="M150 30 L270 150 L150 270 L30 150 Z" />
        <path d="M150 90 L210 150 L150 210 L90 150 Z" />
      </g>

      {/* orthogonal rule */}
      <g fill="none" stroke="var(--rule-hi)" strokeWidth="1">
        <path d="M90 90 L210 90 L210 210 L90 210 Z" />
      </g>

      {/* centre — the fired mark */}
      <circle cx="150" cy="150" r="26" fill="none" stroke="var(--ochre)" strokeWidth="1.25" />
      <circle cx="150" cy="150" r="4.5" fill="var(--ochre)" />

      {/* corner registration marks */}
      <g stroke="var(--ochre-deep)" strokeWidth="1">
        <path d="M14 30 H30 V14" fill="none" />
        <path d="M286 30 H270 V14" fill="none" />
        <path d="M14 270 H30 V286" fill="none" />
        <path d="M286 270 H270 V286" fill="none" />
      </g>
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* Background fields                                                    */
/* ------------------------------------------------------------------ */

const FIELD = [60, 180, 300, 420, 540];

/** A wide pulli-kolam field: dot matrix, loop lattice, diamond rule.
 *  Used as a low-opacity background layer. */
export function KolamField({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 600 600"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      {/* the loops drawn around each pulli */}
      <g fill="none" stroke="var(--rule-hi)" strokeWidth="1">
        {FIELD.map((y) => FIELD.map((x) => <circle key={`l${x}-${y}`} cx={x} cy={y} r="60" />))}
      </g>

      {/* diamond rule threaded through the loops */}
      <g fill="none" stroke="var(--madder)" strokeWidth="1" opacity="0.85">
        <path d="M300 60 L540 300 L300 540 L60 300 Z" />
        <path d="M300 180 L420 300 L300 420 L180 300 Z" />
      </g>

      {/* orthogonal rule */}
      <g fill="none" stroke="var(--ochre-deep)" strokeWidth="1" opacity="0.8">
        <path d="M180 180 H420 V420 H180 Z" />
      </g>

      {/* the pulli themselves */}
      <g fill="var(--chalk-dim)">
        {FIELD.map((y) => FIELD.map((x) => <circle key={`d${x}-${y}`} cx={x} cy={y} r="3" />))}
      </g>
    </svg>
  );
}

/** Concentric arcs — a mural halo. Rings are broken so the geometry reads
 *  as drawn rather than printed. */
export function ArcStack({ className }: { className?: string }) {
  const rings = [
    { r: 42, stroke: "var(--ochre)", dash: "3 9" },
    { r: 74, stroke: "var(--rule-hi)", dash: "" },
    { r: 106, stroke: "var(--madder)", dash: "58 26" },
    { r: 138, stroke: "var(--rule-hi)", dash: "2 12" },
    { r: 170, stroke: "var(--ochre-deep)", dash: "120 60" },
    { r: 202, stroke: "var(--rule)", dash: "" },
  ];
  return (
    <svg
      className={className}
      viewBox="0 0 440 440"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      <g fill="none" strokeWidth="1">
        {rings.map((ring) => (
          <circle
            key={ring.r}
            cx="220"
            cy="220"
            r={ring.r}
            stroke={ring.stroke}
            strokeDasharray={ring.dash || undefined}
          />
        ))}
      </g>
      <g stroke="var(--rule-hi)" strokeWidth="1">
        <path d="M220 6 V70" />
        <path d="M220 370 V434" />
        <path d="M6 220 H70" />
        <path d="M370 220 H434" />
      </g>
      <circle cx="220" cy="220" r="5" fill="var(--madder)" />
    </svg>
  );
}

/** A small square glyph for a single strand of the platform.
 *  `index` (0-3) picks one of four kolam figures. */
export function StrandGlyph({ index, className }: { index: number; className?: string }) {
  const figures = [
    // 01 — the seed: a dot inside an opening square
    <g key="a" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M12 12 H68 V68 H12 Z" />
      <path d="M26 40 L40 26 L54 40 L40 54 Z" />
      <circle cx="40" cy="40" r="3.5" fill="currentColor" stroke="none" />
    </g>,
    // 02 — the ledger: stacked rules with a seal
    <g key="b" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M14 20 H66 M14 34 H50 M14 48 H58 M14 62 H40" />
      <circle cx="58" cy="58" r="9" />
    </g>,
    // 03 — the weave: interlocked loops
    <g key="c" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="30" cy="30" r="16" />
      <circle cx="50" cy="50" r="16" />
      <path d="M30 14 V8 M50 66 V72" />
    </g>,
    // 04 — the measure: a rising rule
    <g key="d" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M12 68 H68" />
      <path d="M22 68 V52 M36 68 V40 M50 68 V28 M64 68 V16" />
      <circle cx="64" cy="16" r="3.5" fill="currentColor" stroke="none" />
    </g>,
  ];
  return (
    <svg
      className={className}
      viewBox="0 0 80 80"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      {figures[index % figures.length]}
    </svg>
  );
}

/** A single horizontal kolam rule — used to separate bands. */
export function RuleWeave({ className }: { className?: string }) {
  const cells = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
  return (
    <svg
      className={className}
      viewBox="0 0 480 24"
      preserveAspectRatio="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      <g fill="none" stroke="var(--rule-hi)" strokeWidth="1">
        {cells.map((i) => (
          <path key={i} d={`M${i * 40} 12 q20 -14 40 0 q20 14 40 0`} />
        ))}
      </g>
    </svg>
  );
}
